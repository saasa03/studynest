# # 🎓 Academia Studenti

**Piattaforma di gestione dello studio per studenti italiani**

## 🌟 Funzionalità

### 🎯 Core Features
- **Dashboard** con statistiche giornaliere e settimanali
- **Focus Mode** con timer e frasi motivazionali IA (Claude Sonnet 4)
- **Gestione Materie** con colori personalizzati e obiettivi
- **Sistema Voti** con calcolo automatico della media
- **Sistema Crediti** (5 crediti ogni 30 minuti di studio)
- **Profilo Personale** con livelli e achievements
- **Autenticazione** completa (JWT)

### 🤖 Integrazione IA
- Frasi motivazionali generate da **Claude Sonnet 4**
- Personalizzate per ogni materia di studio
- Completamente in italiano

## 🛠️ Stack Tecnologico

### Backend
- **FastAPI** (Python)
- **MongoDB** database
- **JWT** authentication
- **Emergent Integrations** per IA

### Frontend  
- **React 19**
- **Tailwind CSS**
- **Shadcn/UI** components
- **Lucide React** icons

## 📦 Installazione Locale

### Prerequisiti
- Python 3.11+
- Node.js 18+
- MongoDB

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Configura le variabili ambiente nel file .env
uvicorn server:app --reload --host 0.0.0.0 --port 8001
```

### Frontend Setup
```bash
cd frontend
yarn install
cp .env.example .env
# Configura REACT_APP_BACKEND_URL nel file .env
yarn start
```

## 🚀 Deploy in Produzione

### 1. Backend (Railway/Render)
- Carica su GitHub
- Connetti a Railway/Render  
- Aggiungi variabili ambiente
- Deploy automatico

### 2. Frontend (Vercel/Netlify)
- Connetti repository GitHub
- Configura build command: `yarn build`
- Deploy automatico

### 3. Database
- MongoDB Atlas (cloud)
- O incluso nel servizio backend

## 🔐 Variabili Ambiente

### Backend (.env)
```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=academia_studenti  
EMERGENT_LLM_KEY=sk-emergent-...
CORS_ORIGINS=*
```

### Frontend (.env)
```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

## 📸 Screenshots

### Dashboard
![Dashboard](docs/dashboard.png)

### Focus Mode
![Focus Mode](docs/focus-mode.png)

### Gestione Materie
![Subjects](docs/subjects.png)

## 🧪 Testing

```bash
# Backend tests
python -m pytest backend_test.py

# Frontend tests  
yarn test
```

## 📄 Licenza

MIT License - Vedi [LICENSE](LICENSE) per dettagli.

## 🤝 Contributi

1. Fork del repository
2. Crea un branch (`git checkout -b feature/amazing-feature`)  
3. Commit (`git commit -m 'Add amazing feature'`)
4. Push (`git push origin feature/amazing-feature`)
5. Apri una Pull Request

## 📞 Supporto

Per supporto tecnico o domande:
- Apri un **Issue** su GitHub
- Invia email a: support@academiastudenti.com

---

**Fatto con ❤️ per gli studenti italiani** 🇮🇹

*Organizza il tuo studio, raggiungi i tuoi obiettivi accademici!*
