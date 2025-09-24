from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone, timedelta
import hashlib
import jwt
from passlib.context import CryptContext
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "academiastudenti2025secretkey"
ALGORITHM = "HS256"

# Create the main app without a prefix
app = FastAPI(title="Academia Studenti API", description="API for student study management")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# AI Chat setup
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

# Pydantic Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: str
    password_hash: str
    full_name: Optional[str] = None
    avatar: str = "default.png"
    credits: int = 0
    total_study_minutes: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserProfile(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str]
    avatar: str
    credits: int
    total_study_minutes: int

class Subject(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    color: str = "#3B82F6"  # Default blue
    target_hours_per_week: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SubjectCreate(BaseModel):
    name: str
    color: str = "#3B82F6"
    target_hours_per_week: int = 0

class Grade(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    subject_id: str
    grade: float
    max_grade: float = 30.0
    exam_name: str
    exam_date: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class GradeCreate(BaseModel):
    subject_id: str
    grade: float
    max_grade: float = 30.0
    exam_name: str
    exam_date: datetime

class StudySession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    subject_id: str
    duration_minutes: int
    credits_earned: int
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    motivational_phrases: List[str] = []

class StudySessionCreate(BaseModel):
    subject_id: str
    duration_minutes: int

class MotivationalPhraseRequest(BaseModel):
    context: str = "general study"

class DashboardData(BaseModel):
    today_sessions: int
    today_minutes: int
    today_credits: int
    weekly_minutes: int
    average_grade: float
    total_subjects: int
    recent_sessions: List[Dict]
    upcoming_goals: List[Dict]

# Utility functions
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    user = await db.users.find_one({"username": username})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return User(**user)

async def generate_motivational_phrase(context: str = "general study") -> str:
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id="motivational-phrases",
            system_message="Sei un coach motivazionale per studenti italiani. Genera una frase breve e motivazionale (max 15 parole) per incoraggiare lo studio. Usa un tono positivo ed energico."
        ).with_model("anthropic", "claude-3-7-sonnet-20250219")
        
        user_message = UserMessage(
            text=f"Genera una frase motivazionale per uno studente che sta studiando: {context}. Rispondi solo con la frase, senza spiegazioni."
        )
        
        response = await chat.send_message(user_message)
        return response.strip() if response else "Continua così, stai facendo un ottimo lavoro!"
        
    except Exception as e:
        logging.error(f"Error generating motivational phrase: {e}")
        default_phrases = [
            "Ogni minuto di studio è un passo verso il successo!",
            "La disciplina è il ponte tra obiettivi e risultati.",
            "Stai investendo nel tuo futuro, continua così!",
            "Il sapere è l'unica ricchezza che nessuno può rubarti.",
            "Oggi è più vicino di ieri ai tuoi obiettivi!"
        ]
        import random
        return random.choice(default_phrases)

# Authentication Routes
@api_router.post("/auth/register")
async def register_user(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({
        "$or": [
            {"username": user_data.username},
            {"email": user_data.email}
        ]
    })
    
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username or email already registered"
        )
    
    # Create new user
    hashed_password = hash_password(user_data.password)
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name
    )
    
    user_dict = user.dict()
    user_dict['created_at'] = user_dict['created_at'].isoformat()
    await db.users.insert_one(user_dict)
    
    # Create access token
    access_token = create_access_token({"sub": user.username})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserProfile(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            avatar=user.avatar,
            credits=user.credits,
            total_study_minutes=user.total_study_minutes
        )
    }

@api_router.post("/auth/login")
async def login_user(login_data: UserLogin):
    user = await db.users.find_one({"username": login_data.username})
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Incorrect username or password"
        )
    
    if not verify_password(login_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=400,
            detail="Incorrect username or password"
        )
    
    access_token = create_access_token({"sub": user["username"]})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserProfile(**user)
    }

@api_router.get("/auth/profile", response_model=UserProfile)
async def get_profile(current_user: User = Depends(get_current_user)):
    return UserProfile(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        avatar=current_user.avatar,
        credits=current_user.credits,
        total_study_minutes=current_user.total_study_minutes
    )

# Subject Routes
@api_router.post("/subjects", response_model=Subject)
async def create_subject(
    subject_data: SubjectCreate,
    current_user: User = Depends(get_current_user)
):
    subject = Subject(
        user_id=current_user.id,
        **subject_data.dict()
    )
    
    subject_dict = subject.dict()
    subject_dict['created_at'] = subject_dict['created_at'].isoformat()
    await db.subjects.insert_one(subject_dict)
    
    return subject

@api_router.get("/subjects", response_model=List[Subject])
async def get_subjects(current_user: User = Depends(get_current_user)):
    subjects = await db.subjects.find({"user_id": current_user.id}).to_list(100)
    for subject in subjects:
        if isinstance(subject.get('created_at'), str):
            subject['created_at'] = datetime.fromisoformat(subject['created_at'])
    return [Subject(**subject) for subject in subjects]

@api_router.delete("/subjects/{subject_id}")
async def delete_subject(
    subject_id: str,
    current_user: User = Depends(get_current_user)
):
    result = await db.subjects.delete_one({
        "id": subject_id,
        "user_id": current_user.id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    return {"message": "Subject deleted successfully"}

# Grade Routes
@api_router.post("/grades", response_model=Grade)
async def add_grade(
    grade_data: GradeCreate,
    current_user: User = Depends(get_current_user)
):
    # Verify subject belongs to user
    subject = await db.subjects.find_one({
        "id": grade_data.subject_id,
        "user_id": current_user.id
    })
    
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    grade = Grade(
        user_id=current_user.id,
        **grade_data.dict()
    )
    
    grade_dict = grade.dict()
    grade_dict['exam_date'] = grade_dict['exam_date'].isoformat()
    grade_dict['created_at'] = grade_dict['created_at'].isoformat()
    await db.grades.insert_one(grade_dict)
    
    return grade

@api_router.get("/grades", response_model=List[Grade])
async def get_grades(current_user: User = Depends(get_current_user)):
    grades = await db.grades.find({"user_id": current_user.id}).to_list(100)
    for grade in grades:
        if isinstance(grade.get('exam_date'), str):
            grade['exam_date'] = datetime.fromisoformat(grade['exam_date'])
        if isinstance(grade.get('created_at'), str):
            grade['created_at'] = datetime.fromisoformat(grade['created_at'])
    return [Grade(**grade) for grade in grades]

# Study Session Routes
@api_router.post("/study-sessions", response_model=StudySession)
async def create_study_session(
    session_data: StudySessionCreate,
    current_user: User = Depends(get_current_user)
):
    # Verify subject belongs to user
    subject = await db.subjects.find_one({
        "id": session_data.subject_id,
        "user_id": current_user.id
    })
    
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    # Calculate credits (5 credits per 30 minutes)
    credits_earned = (session_data.duration_minutes // 30) * 5
    
    # Generate motivational phrases
    motivational_phrases = []
    try:
        phrase = await generate_motivational_phrase(f"studying {subject['name']}")
        motivational_phrases.append(phrase)
    except:
        pass
    
    session = StudySession(
        user_id=current_user.id,
        subject_id=session_data.subject_id,
        duration_minutes=session_data.duration_minutes,
        credits_earned=credits_earned,
        motivational_phrases=motivational_phrases
    )
    
    # Update user credits and total study time
    await db.users.update_one(
        {"id": current_user.id},
        {
            "$inc": {
                "credits": credits_earned,
                "total_study_minutes": session_data.duration_minutes
            }
        }
    )
    
    session_dict = session.dict()
    session_dict['date'] = session_dict['date'].isoformat()
    await db.study_sessions.insert_one(session_dict)
    
    return session

@api_router.get("/study-sessions", response_model=List[StudySession])
async def get_study_sessions(current_user: User = Depends(get_current_user)):
    sessions = await db.study_sessions.find({"user_id": current_user.id}).sort("date", -1).to_list(100)
    for session in sessions:
        if isinstance(session.get('date'), str):
            session['date'] = datetime.fromisoformat(session['date'])
    return [StudySession(**session) for session in sessions]

# Motivational Phrase Route
@api_router.post("/motivational-phrase")
async def get_motivational_phrase(
    request: MotivationalPhraseRequest,
    current_user: User = Depends(get_current_user)
):
    phrase = await generate_motivational_phrase(request.context)
    return {"phrase": phrase}

# Dashboard Route
@api_router.get("/dashboard", response_model=DashboardData)
async def get_dashboard_data(current_user: User = Depends(get_current_user)):
    today = datetime.now(timezone.utc).date()
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    # Today's sessions
    today_sessions = await db.study_sessions.count_documents({
        "user_id": current_user.id,
        "date": {
            "$gte": datetime.combine(today, datetime.min.time()),
            "$lt": datetime.combine(today + timedelta(days=1), datetime.min.time())
        }
    })
    
    # Today's minutes and credits
    today_sessions_data = await db.study_sessions.find({
        "user_id": current_user.id,
        "date": {
            "$gte": datetime.combine(today, datetime.min.time()),
            "$lt": datetime.combine(today + timedelta(days=1), datetime.min.time())
        }
    }).to_list(100)
    
    today_minutes = sum(session.get('duration_minutes', 0) for session in today_sessions_data)
    today_credits = sum(session.get('credits_earned', 0) for session in today_sessions_data)
    
    # Weekly minutes
    weekly_sessions = await db.study_sessions.find({
        "user_id": current_user.id,
        "date": {"$gte": week_ago}
    }).to_list(1000)
    
    weekly_minutes = sum(session.get('duration_minutes', 0) for session in weekly_sessions)
    
    # Average grade
    grades = await db.grades.find({"user_id": current_user.id}).to_list(1000)
    average_grade = 0
    if grades:
        total_points = sum(grade.get('grade', 0) for grade in grades)
        average_grade = round(total_points / len(grades), 2)
    
    # Total subjects
    total_subjects = await db.subjects.count_documents({"user_id": current_user.id})
    
    # Recent sessions (last 5)
    recent_sessions_data = await db.study_sessions.find({
        "user_id": current_user.id
    }).sort("date", -1).limit(5).to_list(5)
    
    recent_sessions = []
    for session in recent_sessions_data:
        subject = await db.subjects.find_one({"id": session.get('subject_id')})
        recent_sessions.append({
            "subject_name": subject.get('name', 'Unknown') if subject else 'Unknown',
            "duration_minutes": session.get('duration_minutes', 0),
            "date": session.get('date', '').split('T')[0] if session.get('date') else '',
            "credits_earned": session.get('credits_earned', 0)
        })
    
    return DashboardData(
        today_sessions=today_sessions,
        today_minutes=today_minutes,
        today_credits=today_credits,
        weekly_minutes=weekly_minutes,
        average_grade=average_grade,
        total_subjects=total_subjects,
        recent_sessions=recent_sessions,
        upcoming_goals=[]  # Will be implemented later
    )

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()