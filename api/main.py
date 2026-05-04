import sys, os, json, secrets, smtplib, asyncio, random
import csv, io
import httpx
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Depends, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import bcrypt
from jose import JWTError, jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()


# ══════════════════════════════════════════════════════════════════════════════
#  BASE DE DONNÉES
# ══════════════════════════════════════════════════════════════════════════════

engine = create_engine("sqlite:///./users.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════
#  MODÈLES
# ══════════════════════════════════════════════════════════════════════════════

class User(Base):
    __tablename__ = "users"
    id              = Column(Integer, primary_key=True, index=True)
    email           = Column(String, unique=True, index=True, nullable=False)
    pseudo          = Column(String, nullable=False)
    password        = Column(String, nullable=False)
    avatar          = Column(Text, nullable=True)
    preferred_lang  = Column(String, default="fr", nullable=False)
    is_admin        = Column(Boolean, default=False, nullable=False)
    onboarding_done = Column(Boolean, default=False, nullable=False)

class Anime(Base):
    __tablename__ = "anime"
    id               = Column(Integer, primary_key=True, index=True)
    title            = Column(String, nullable=False)
    title_en         = Column(String, nullable=True)
    cover_url        = Column(String, nullable=True)
    genres           = Column(Text, nullable=True)
    anime_status     = Column(String, nullable=True)
    type             = Column(String, nullable=True)
    studio           = Column(String, nullable=True)
    author           = Column(String, nullable=True)
    age_rating       = Column(Integer, nullable=True)
    seasons_total    = Column(Integer, nullable=True)
    episodes_total   = Column(Integer, nullable=True)
    episode_duration = Column(Integer, nullable=True)
    air_start        = Column(String, nullable=True)
    air_end          = Column(String, nullable=True)
    trailer_url      = Column(String, nullable=True)
    opening_url      = Column(String, nullable=True)
    news_url         = Column(String, nullable=True)
    crunchyroll_url  = Column(String, nullable=True)
    franime_url      = Column(String, nullable=True)
    anime_sama       = Column(String, nullable=True)
    description_en   = Column(Text, nullable=True)
    description_fr   = Column(Text, nullable=True)
    new_season_info  = Column(Text, nullable=True)
    platforms        = Column(Text, nullable=True)
    added_by         = Column(Integer, ForeignKey("users.id"), nullable=True)
    anilist_id       = Column(Integer, nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_archived      = Column(Boolean, default=False, nullable=False)

class AnimePending(Base):
    __tablename__ = "anime_pending"
    id          = Column(Integer, primary_key=True, index=True)
    anime_data  = Column(Text, nullable=False)
    proposed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    proposed_at = Column(DateTime, default=datetime.utcnow)
    status      = Column(String, default="pending", nullable=False)
    admin_note  = Column(Text, nullable=True)

class AnimeModification(Base):
    __tablename__ = "anime_modifications"
    id            = Column(Integer, primary_key=True, index=True)
    anime_id      = Column(Integer, ForeignKey("anime.id"), nullable=False)
    modified_by   = Column(Integer, ForeignKey("users.id"), nullable=False)
    field_changed = Column(String, nullable=False)
    old_value     = Column(Text, nullable=True)
    new_value     = Column(Text, nullable=True)
    modified_at   = Column(DateTime, default=datetime.utcnow)

class AnimeReport(Base):
    __tablename__ = "anime_reports"
    id             = Column(Integer, primary_key=True, index=True)
    anime_id       = Column(Integer, ForeignKey("anime.id"), nullable=False)
    reported_by    = Column(Integer, ForeignKey("users.id"), nullable=False)
    message        = Column(Text, nullable=False)
    status         = Column(String, default="pending", nullable=False)
    admin_response = Column(Text, nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)

class Watchlist(Base):
    __tablename__ = "watchlists"
    id                = Column(Integer, primary_key=True, index=True)
    user_id           = Column(Integer, ForeignKey("users.id"), nullable=False)
    name              = Column(String, nullable=False)
    cover_url         = Column(String, nullable=True)
    is_public         = Column(Boolean, default=False, nullable=False)
    public_token      = Column(String, unique=True, nullable=True)
    created_at        = Column(DateTime, default=datetime.utcnow)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    column_order      = Column(Text, nullable=True)
    column_visibility = Column(Text, nullable=True)
    sort_field        = Column(String, nullable=True)
    sort_direction    = Column(String, nullable=True)
    group_by_status   = Column(Boolean, default=False, nullable=False)

class WatchlistEntry(Base):
    __tablename__ = "watchlist_entries"
    id               = Column(Integer, primary_key=True, index=True)
    watchlist_id     = Column(Integer, ForeignKey("watchlists.id"), nullable=False)
    anime_id         = Column(Integer, ForeignKey("anime.id"), nullable=False)
    watch_status     = Column(String, nullable=True)
    score            = Column(Float, nullable=True)
    episodes_watched = Column(Integer, nullable=True)
    seasons_watched  = Column(Integer, nullable=True)
    watch_start      = Column(String, nullable=True)
    watch_end        = Column(String, nullable=True)
    watch_date       = Column(String, nullable=True)
    personal_review  = Column(Text, nullable=True)
    extra_info       = Column(Text, nullable=True)
    new_season_note  = Column(Text, nullable=True)
    platform         = Column(String, nullable=True)
    is_favorite      = Column(Boolean, default=False, nullable=False)
    is_to_rewatch    = Column(Boolean, default=False, nullable=False)
    is_pinned        = Column(Boolean, default=False, nullable=False)
    custom_tags      = Column(Text, nullable=True)
    sort_order       = Column(Integer, nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WatchlistSeasonTracking(Base):
    __tablename__ = "watchlist_season_tracking"
    id               = Column(Integer, primary_key=True, index=True)
    entry_id         = Column(Integer, ForeignKey("watchlist_entries.id"), nullable=False)
    season_number    = Column(Integer, nullable=False)
    episodes_watched = Column(Integer, nullable=True)
    episodes_total   = Column(Integer, nullable=True)
    status           = Column(String, nullable=True)
    watch_start      = Column(String, nullable=True)
    watch_end        = Column(String, nullable=True)

class Notification(Base):
    __tablename__ = "notifications"
    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    type       = Column(String, nullable=False)
    title_fr   = Column(String, nullable=True)
    title_en   = Column(String, nullable=True)
    body_fr    = Column(Text, nullable=True)
    body_en    = Column(Text, nullable=True)
    link       = Column(String, nullable=True)
    is_read    = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class AdminBroadcast(Base):
    __tablename__ = "admin_broadcasts"
    id              = Column(Integer, primary_key=True, index=True)
    title_fr        = Column(String, nullable=True)
    title_en        = Column(String, nullable=True)
    body_fr         = Column(Text, nullable=True)
    body_en         = Column(Text, nullable=True)
    scheduled_at    = Column(DateTime, nullable=True)
    sent_at         = Column(DateTime, nullable=True)
    sent_by         = Column(Integer, ForeignKey("users.id"), nullable=True)
    recipient_count = Column(Integer, nullable=True)

class Changelog(Base):
    __tablename__ = "changelog"
    id           = Column(Integer, primary_key=True, index=True)
    title_fr     = Column(String, nullable=True)
    title_en     = Column(String, nullable=True)
    body_fr      = Column(Text, nullable=True)
    body_en      = Column(Text, nullable=True)
    published_at = Column(DateTime, default=datetime.utcnow)
    published_by = Column(Integer, ForeignKey("users.id"), nullable=True)

class UserNotificationPrefs(Base):
    __tablename__ = "user_notification_prefs"
    user_id           = Column(Integer, ForeignKey("users.id"), primary_key=True)
    lang              = Column(String, default="fr", nullable=False)
    notify_new_season = Column(Boolean, default=True, nullable=False)
    notify_new_anime  = Column(Boolean, default=True, nullable=False)
    notify_admin      = Column(Boolean, default=True, nullable=False)
    notify_email      = Column(Boolean, default=True, nullable=False)
    notify_inapp      = Column(Boolean, default=True, nullable=False)

Base.metadata.create_all(bind=engine)


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG & AUTH
# ══════════════════════════════════════════════════════════════════════════════

ALGORITHM     = "HS256"
SMTP_EMAIL    = "noreply.pi5.web@gmail.com"
SECRET_KEY    = os.getenv("SECRET_KEY")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")

reset_tokens = {}  # volatile — perdu au redémarrage (connu)

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_token(email: str) -> str:
    expire = datetime.utcnow() + timedelta(days=30)
    return jwt.encode({"sub": email, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None

def send_reset_email(email: str, token: str):
    reset_url = f"http://127.0.0.1:61275/reset-password.html?token={token}"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Réinitialisation de ton mot de passe — Pi"
    msg["From"]    = SMTP_EMAIL
    msg["To"]      = email
    html = f"""
    <html><body style="font-family: sans-serif; background: #0f0f11; color: #e0e0e0; padding: 2rem;">
    <div style="max-width: 480px; margin: auto; background: #1a1a1f; border-radius: 12px; padding: 2rem; border: 1px solid #2a2a2e;">
        <h2 style="color: #6c63ff;">Réinitialisation du mot de passe</h2>
        <p>Tu as demandé à réinitialiser ton mot de passe sur <strong>Pi</strong>.</p>
        <a href="{reset_url}" style="display:inline-block; margin: 1.5rem 0; padding: 0.75rem 1.5rem; background: linear-gradient(135deg, #6c63ff, #4f46e5); color: #fff; border-radius: 8px; text-decoration: none; font-weight: bold;">
            Choisir un nouveau mot de passe
        </a>
        <p style="color: #666; font-size: 0.85rem;">Ce lien expire dans 15 minutes.</p>
    </div>
    </body></html>
    """
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.sendmail(SMTP_EMAIL, email, msg.as_string())


# ══════════════════════════════════════════════════════════════════════════════
#  APP
# ══════════════════════════════════════════════════════════════════════════════

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO : restreindre en prod
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════════════════
#  SCHÉMAS PYDANTIC
# ══════════════════════════════════════════════════════════════════════════════

class RegisterSchema(BaseModel):
    email: EmailStr
    pseudo: str
    password: str

class LoginSchema(BaseModel):
    email: EmailStr
    password: str

class UpdatePseudoSchema(BaseModel):
    pseudo: str

class UpdatePasswordSchema(BaseModel):
    current_password: str
    new_password: str

class UpdateEmailSchema(BaseModel):
    new_email: EmailStr

class UpdateAvatarSchema(BaseModel):
    avatar: Optional[str]

class ForgotPasswordSchema(BaseModel):
    email: EmailStr

class ResetPasswordSchema(BaseModel):
    token: str
    new_password: str

class AnimeCreateSchema(BaseModel):
    title:            str
    title_en:         Optional[str]  = None
    cover_url:        Optional[str]  = None
    genres:           Optional[str]  = None
    anime_status:     Optional[str]  = None
    type:             Optional[str]  = None
    studio:           Optional[str]  = None
    author:           Optional[str]  = None
    age_rating:       Optional[int]  = None
    seasons_total:    Optional[int]  = None
    episodes_total:   Optional[int]  = None
    episode_duration: Optional[int]  = None
    air_start:        Optional[str]  = None
    air_end:          Optional[str]  = None
    trailer_url:      Optional[str]  = None
    opening_url:      Optional[str]  = None
    news_url:         Optional[str]  = None
    crunchyroll_url:  Optional[str]  = None
    franime_url:      Optional[str]  = None
    anime_sama:       Optional[str]  = None
    description_en:   Optional[str]  = None
    description_fr:   Optional[str]  = None
    new_season_info:  Optional[str]  = None
    platforms:        Optional[str]  = None
    anilist_id:       Optional[int]  = None

class AnimeUpdateSchema(AnimeCreateSchema):
    # Hérite d'AnimeCreateSchema mais rend le titre optionnel
    # pour ne modifier qu'un seul champ sans renvoyer toute la fiche.
    title: Optional[str] = None

class ProposeAnimeSchema(BaseModel):
    anime_data: str  # JSON stringifié

class RejectSchema(BaseModel):
    note_fr: str
    note_en: str

class ReportSchema(BaseModel):
    message: str

class WatchlistCreateSchema(BaseModel):
    name: str
    is_public: Optional[bool] = False

class WatchlistUpdateSchema(BaseModel):
    name:              Optional[str]  = None
    cover_url:         Optional[str]  = None
    is_public:         Optional[bool] = None
    column_order:      Optional[str]  = None
    column_visibility: Optional[str]  = None
    sort_field:        Optional[str]  = None
    sort_direction:    Optional[str]  = None
    group_by_status:   Optional[bool] = None

class EntryCreateSchema(BaseModel):
    anime_id:         int
    watch_status:     Optional[str]   = None
    score:            Optional[float] = None
    episodes_watched: Optional[int]   = None
    seasons_watched:  Optional[int]   = None
    watch_start:      Optional[str]   = None
    watch_end:        Optional[str]   = None
    watch_date:       Optional[str]   = None
    personal_review:  Optional[str]   = None
    extra_info:       Optional[str]   = None
    new_season_note:  Optional[str]   = None
    platform:         Optional[str]   = None
    is_favorite:      Optional[bool]  = False
    is_to_rewatch:    Optional[bool]  = False
    is_pinned:        Optional[bool]  = False
    custom_tags:      Optional[str]   = None

class EntryUpdateSchema(EntryCreateSchema):
    anime_id: Optional[int] = None


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def get_current_user(authorization: str = Header(...), db: Session = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    email = decode_token(token)
    if not email:
        raise HTTPException(status_code=401, detail="Token invalide")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return user

def require_admin(current_user=Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Accès refusé")
    return current_user

def anime_to_dict(anime: Anime) -> dict:
    return {
        "id":               anime.id,
        "title":            anime.title,
        "title_en":         anime.title_en,
        "cover_url":        anime.cover_url,
        "genres":           json.loads(anime.genres) if anime.genres else [],
        "anime_status":     anime.anime_status,
        "type":             anime.type,
        "studio":           anime.studio,
        "author":           anime.author,
        "age_rating":       anime.age_rating,
        "seasons_total":    anime.seasons_total,
        "episodes_total":   anime.episodes_total,
        "episode_duration": anime.episode_duration,
        "air_start":        anime.air_start,
        "air_end":          anime.air_end,
        "trailer_url":      anime.trailer_url,
        "opening_url":      anime.opening_url,
        "news_url":         anime.news_url,
        "crunchyroll_url":  anime.crunchyroll_url,
        "franime_url":      anime.franime_url,
        "anime_sama":       anime.anime_sama,
        "description_en":   anime.description_en,
        "description_fr":   anime.description_fr,
        "new_season_info":  anime.new_season_info,
        "platforms":        json.loads(anime.platforms) if anime.platforms else [],
        "anilist_id":       anime.anilist_id,
        "created_at":       anime.created_at.isoformat() if anime.created_at else None,
        "updated_at":       anime.updated_at.isoformat() if anime.updated_at else None,
    }

def entry_to_dict(entry: WatchlistEntry, anime: Anime = None) -> dict:
    d = {
        "id":               entry.id,
        "watchlist_id":     entry.watchlist_id,
        "anime_id":         entry.anime_id,
        "watch_status":     entry.watch_status,
        "score":            entry.score,
        "episodes_watched": entry.episodes_watched,
        "seasons_watched":  entry.seasons_watched,
        "watch_start":      entry.watch_start,
        "watch_end":        entry.watch_end,
        "watch_date":       entry.watch_date,
        "personal_review":  entry.personal_review,
        "extra_info":       entry.extra_info,
        "new_season_note":  entry.new_season_note,
        "platform":         entry.platform,
        "is_favorite":      entry.is_favorite,
        "is_to_rewatch":    entry.is_to_rewatch,
        "is_pinned":        entry.is_pinned,
        "custom_tags":      json.loads(entry.custom_tags) if entry.custom_tags else [],
        "sort_order":       entry.sort_order,
        "created_at":       entry.created_at.isoformat() if entry.created_at else None,
    }
    # Embed les données de base de l'animé pour éviter un 2e appel côté frontend
    if anime:
        d["anime"] = {
            "title":     anime.title,
            "cover_url": anime.cover_url,
            "type":      anime.type,
            "genres":    json.loads(anime.genres) if anime.genres else [],
        }
    return d

async def translate_to_french(text: str) -> Optional[str]:
    # Retourne None si pas de clé ou échec — le frontend affichera le synopsis EN avec un badge
    if not DEEPL_API_KEY or not text:
        return None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api-free.deepl.com/v2/translate",
                data={"auth_key": DEEPL_API_KEY, "text": text, "source_lang": "EN", "target_lang": "FR"}
            )
            return resp.json()["translations"][0]["text"]
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES — AUTH
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/register")
def register(data: RegisterSchema, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    user = User(email=data.email, pseudo=data.pseudo, password=hash_password(data.password))
    db.add(user)
    db.commit()
    return {"token": create_token(data.email), "pseudo": data.pseudo}

@app.post("/login")
def login(data: LoginSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    return {"token": create_token(data.email), "pseudo": user.pseudo}

@app.get("/me")
def me(current_user=Depends(get_current_user)):
    return {
        "email":          current_user.email,
        "pseudo":         current_user.pseudo,
        "avatar":         current_user.avatar,
        "is_admin":       current_user.is_admin,
        "preferred_lang": current_user.preferred_lang,
    }

@app.put("/update/pseudo")
def update_pseudo(data: UpdatePseudoSchema, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.pseudo = data.pseudo
    db.commit()
    return {"message": "Pseudo mis à jour"}

@app.put("/update/password")
def update_password(data: UpdatePasswordSchema, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(data.current_password, current_user.password):
        raise HTTPException(status_code=401, detail="Mot de passe actuel incorrect")
    current_user.password = hash_password(data.new_password)
    db.commit()
    return {"message": "Mot de passe mis à jour"}

@app.put("/update/email")
def update_email(data: UpdateEmailSchema, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.new_email).first():
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    current_user.email = data.new_email
    db.commit()
    return {"message": "Email mis à jour", "token": create_token(data.new_email)}

@app.put("/update/avatar")
def update_avatar(data: UpdateAvatarSchema, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.avatar = data.avatar
    db.commit()
    return {"message": "Avatar mis à jour"}

@app.post("/forgot-password")
def forgot_password(data: ForgotPasswordSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if user:
        token = secrets.token_urlsafe(32)
        reset_tokens[token] = data.email
        try:
            send_reset_email(data.email, token)
        except Exception:
            raise HTTPException(status_code=500, detail="Erreur envoi email")
    return {"message": "Si cet email existe, un lien a été envoyé."}

@app.post("/reset-password")
def reset_password(data: ResetPasswordSchema, db: Session = Depends(get_db)):
    email = reset_tokens.get(data.token)
    if not email:
        raise HTTPException(status_code=400, detail="Token invalide ou expiré")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    user.password = hash_password(data.new_password)
    db.commit()
    del reset_tokens[data.token]
    return {"message": "Mot de passe réinitialisé"}

@app.delete("/delete")
def delete_account(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(current_user)
    db.commit()
    return {"message": "Compte supprimé"}


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES — CATALOGUE ANIME
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/anime")
def get_anime_list(
    db: Session = Depends(get_db),
    genre:  Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    type:   Optional[str] = Query(None),
    q:      Optional[str] = Query(None),
):
    query = db.query(Anime).filter(Anime.is_archived == False)
    if q:
        query = query.filter(Anime.title.ilike(f"%{q}%"))
    if status:
        query = query.filter(Anime.anime_status == status)
    if type:
        query = query.filter(Anime.type == type)
    if genre:
        # genres est un JSON string → on cherche dans le texte brut
        query = query.filter(Anime.genres.ilike(f"%{genre}%"))
    return [anime_to_dict(a) for a in query.order_by(Anime.title).all()]


@app.get("/anime/anilist/search")
async def search_anilist(q: str = Query(..., min_length=2)):
    """Recherche sur AniList (GraphQL) pour pré-remplir le formulaire d'ajout."""
    gql_query = """
    query ($search: String) {
        Page(perPage: 10) {
            media(search: $search, type: ANIME) {
                id
                title { romaji english }
                coverImage { large }
                genres
                status
                format
                episodes
                duration
                startDate { year month day }
                endDate { year month day }
                studios(isMain: true) { nodes { name } }
                description(asHtml: false)
            }
        }
    }
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                "https://graphql.anilist.co",
                json={"query": gql_query, "variables": {"search": q}},
                timeout=10.0
            )
            results = []
            for media in resp.json()["data"]["Page"]["media"]:
                start   = media.get("startDate", {})
                end     = media.get("endDate", {})
                studios = media.get("studios", {}).get("nodes", [])
                results.append({
                    "anilist_id":       media["id"],
                    "title":            media["title"]["romaji"],
                    "title_en":         media["title"].get("english"),
                    "cover_url":        media["coverImage"]["large"],
                    "genres":           json.dumps(media.get("genres", [])),
                    "anime_status":     media.get("status", "").lower(),
                    "type":             "movie" if media.get("format") == "MOVIE" else "serie",
                    "episodes_total":   media.get("episodes"),
                    "episode_duration": media.get("duration"),
                    "air_start":        f"{start['year']}-{start['month']:02d}-{start['day']:02d}" if start.get("year") else None,
                    "air_end":          f"{end['year']}-{end['month']:02d}-{end['day']:02d}" if end.get("year") else None,
                    "studio":           studios[0]["name"] if studios else None,
                    "description_en":   media.get("description"),
                })
            return results
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Erreur AniList : {str(e)}")


@app.get("/anime/{anime_id}")
def get_anime(anime_id: int, db: Session = Depends(get_db)):
    anime = db.query(Anime).filter(Anime.id == anime_id, Anime.is_archived == False).first()
    if not anime:
        raise HTTPException(status_code=404, detail="Animé introuvable")
    return anime_to_dict(anime)


@app.post("/anime")
async def create_anime(data: AnimeCreateSchema, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if current_user.is_admin:
        description_fr = data.description_fr
        if data.description_en and not description_fr:
            description_fr = await translate_to_french(data.description_en)
        anime = Anime(**data.model_dump(exclude={"description_fr"}), description_fr=description_fr, added_by=current_user.id)
        db.add(anime)
        db.commit()
        db.refresh(anime)
        return {"message": "Animé ajouté", "id": anime.id}
    else:
        # User normal → proposition en attente de validation admin
        pending = AnimePending(anime_data=json.dumps(data.model_dump()), proposed_by=current_user.id)
        db.add(pending)
        db.commit()
        return {"message": "Proposition envoyée, en attente de validation"}


@app.put("/anime/{anime_id}")
def update_anime(anime_id: int, data: AnimeUpdateSchema, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    anime = db.query(Anime).filter(Anime.id == anime_id).first()
    if not anime:
        raise HTTPException(status_code=404, detail="Animé introuvable")
    for field, new_value in data.model_dump(exclude_unset=True).items():
        old_value = getattr(anime, field)
        if old_value != new_value:
            setattr(anime, field, new_value)
            # Trace chaque changement dans l'historique
            db.add(AnimeModification(
                anime_id=anime_id, modified_by=current_user.id,
                field_changed=field, old_value=str(old_value), new_value=str(new_value)
            ))
    db.commit()
    return {"message": "Animé mis à jour"}


@app.delete("/anime/{anime_id}")
def archive_anime(anime_id: int, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    anime = db.query(Anime).filter(Anime.id == anime_id).first()
    if not anime:
        raise HTTPException(status_code=404, detail="Animé introuvable")
    anime.is_archived = True  # archive, ne supprime jamais
    db.commit()
    return {"message": "Animé archivé"}


@app.post("/anime/{anime_id}/report")
def report_anime(anime_id: int, data: ReportSchema, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if not db.query(Anime).filter(Anime.id == anime_id).first():
        raise HTTPException(status_code=404, detail="Animé introuvable")
    db.add(AnimeReport(anime_id=anime_id, reported_by=current_user.id, message=data.message))
    db.commit()
    return {"message": "Signalement envoyé"}


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES — WATCHLISTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/watchlists")
def get_watchlists(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    watchlists = db.query(Watchlist).filter(Watchlist.user_id == current_user.id).all()
    return [
        {
            "id":                w.id,
            "name":              w.name,
            "cover_url":         w.cover_url,
            "is_public":         w.is_public,
            "public_token":      w.public_token,
            "created_at":        w.created_at.isoformat() if w.created_at else None,
            "updated_at":        w.updated_at.isoformat() if w.updated_at else None,
            "column_order":      json.loads(w.column_order) if w.column_order else None,
            "column_visibility": json.loads(w.column_visibility) if w.column_visibility else None,
            "sort_field":        w.sort_field,
            "sort_direction":    w.sort_direction,
            "group_by_status":   w.group_by_status,
            "entry_count":       db.query(WatchlistEntry).filter(WatchlistEntry.watchlist_id == w.id).count(),
        }
        for w in watchlists
    ]


@app.post("/watchlists")
def create_watchlist(data: WatchlistCreateSchema, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    watchlist = Watchlist(
        user_id=current_user.id,
        name=data.name,
        is_public=data.is_public,
        public_token=secrets.token_urlsafe(16)  # généré même si privé, prêt si rendu public
    )
    db.add(watchlist)
    db.commit()
    db.refresh(watchlist)
    return {"message": "Watchlist créée", "id": watchlist.id, "public_token": watchlist.public_token}


@app.put("/watchlists/{watchlist_id}")
def update_watchlist(watchlist_id: int, data: WatchlistUpdateSchema, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    watchlist = db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == current_user.id).first()
    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist introuvable")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(watchlist, field, value)
    db.commit()
    return {"message": "Watchlist mise à jour"}


@app.delete("/watchlists/{watchlist_id}")
def delete_watchlist(watchlist_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    watchlist = db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == current_user.id).first()
    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist introuvable")
    # SQLite ne gère pas les cascade deletes par défaut → suppression manuelle des entrées
    db.query(WatchlistEntry).filter(WatchlistEntry.watchlist_id == watchlist_id).delete()
    db.delete(watchlist)
    db.commit()
    return {"message": "Watchlist supprimée"}


@app.get("/watchlists/share/{token}")
def get_public_watchlist(token: str, db: Session = Depends(get_db)):
    # Route publique — accessible sans connexion
    watchlist = db.query(Watchlist).filter(Watchlist.public_token == token, Watchlist.is_public == True).first()
    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist introuvable ou privée")
    entries = db.query(WatchlistEntry).filter(WatchlistEntry.watchlist_id == watchlist.id).all()
    return {
        "name":    watchlist.name,
        "entries": [entry_to_dict(e, db.query(Anime).filter(Anime.id == e.anime_id).first()) for e in entries]
    }


@app.get("/watchlists/{watchlist_id}/entries")
def get_entries(watchlist_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == current_user.id).first():
        raise HTTPException(status_code=404, detail="Watchlist introuvable")
    entries = db.query(WatchlistEntry).filter(WatchlistEntry.watchlist_id == watchlist_id).all()
    return [entry_to_dict(e, db.query(Anime).filter(Anime.id == e.anime_id).first()) for e in entries]


@app.post("/watchlists/{watchlist_id}/entries")
def add_entry(watchlist_id: int, data: EntryCreateSchema, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == current_user.id).first():
        raise HTTPException(status_code=404, detail="Watchlist introuvable")
    if not db.query(Anime).filter(Anime.id == data.anime_id, Anime.is_archived == False).first():
        raise HTTPException(status_code=404, detail="Animé introuvable")
    if db.query(WatchlistEntry).filter(WatchlistEntry.watchlist_id == watchlist_id, WatchlistEntry.anime_id == data.anime_id).first():
        raise HTTPException(status_code=400, detail="Animé déjà dans la watchlist")
    entry_data = data.model_dump()
    if isinstance(entry_data.get("custom_tags"), list):
        entry_data["custom_tags"] = json.dumps(entry_data["custom_tags"])
    entry = WatchlistEntry(watchlist_id=watchlist_id, **entry_data)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"message": "Animé ajouté", "id": entry.id}


@app.put("/watchlists/{watchlist_id}/entries/{entry_id}")
def update_entry(watchlist_id: int, entry_id: int, data: EntryUpdateSchema, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == current_user.id).first():
        raise HTTPException(status_code=404, detail="Watchlist introuvable")
    entry = db.query(WatchlistEntry).filter(WatchlistEntry.id == entry_id, WatchlistEntry.watchlist_id == watchlist_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entrée introuvable")
    changes = data.model_dump(exclude_unset=True)
    if "custom_tags" in changes and isinstance(changes["custom_tags"], list):
        changes["custom_tags"] = json.dumps(changes["custom_tags"])
    for field, value in changes.items():
        setattr(entry, field, value)
    db.commit()
    return {"message": "Entrée mise à jour"}


@app.delete("/watchlists/{watchlist_id}/entries/{entry_id}")
def delete_entry(watchlist_id: int, entry_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == current_user.id).first():
        raise HTTPException(status_code=404, detail="Watchlist introuvable")
    entry = db.query(WatchlistEntry).filter(WatchlistEntry.id == entry_id, WatchlistEntry.watchlist_id == watchlist_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entrée introuvable")
    db.delete(entry)
    db.commit()
    return {"message": "Entrée supprimée"}


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES — NOTIFICATIONS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/notifications")
def get_notifications(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    notifs = db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).order_by(Notification.created_at.desc()).limit(50).all()
    return [
        {
            "id": n.id, "type": n.type,
            "title_fr": n.title_fr, "title_en": n.title_en,
            "body_fr": n.body_fr,   "body_en": n.body_en,
            "link": n.link,         "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifs
    ]


@app.get("/notifications/unread-count")
def unread_count(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    # Polling léger depuis la cloche — appelé toutes les 60s
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id, Notification.is_read == False
    ).count()
    return {"count": count}


@app.put("/notifications/{notif_id}/read")
def mark_read(notif_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    notif = db.query(Notification).filter(Notification.id == notif_id, Notification.user_id == current_user.id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification introuvable")
    notif.is_read = True
    db.commit()
    return {"message": "Notification lue"}


@app.put("/notifications/read-all")
def mark_all_read(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Notification).filter(
        Notification.user_id == current_user.id, Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"message": "Toutes les notifications lues"}


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES — ADMIN
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/admin/pending")
def get_pending(current_user=Depends(require_admin), db: Session = Depends(get_db)):
    pending = db.query(AnimePending).filter(AnimePending.status == "pending").all()
    return [
        {"id": p.id, "anime_data": json.loads(p.anime_data), "proposed_by": p.proposed_by,
         "proposed_at": p.proposed_at.isoformat() if p.proposed_at else None}
        for p in pending
    ]


@app.post("/admin/pending/{pending_id}/approve")
async def approve_pending(pending_id: int, current_user=Depends(require_admin), db: Session = Depends(get_db)):
    pending = db.query(AnimePending).filter(AnimePending.id == pending_id).first()
    if not pending:
        raise HTTPException(status_code=404, detail="Proposition introuvable")
    anime_data = json.loads(pending.anime_data)
    if anime_data.get("description_en") and not anime_data.get("description_fr"):
        anime_data["description_fr"] = await translate_to_french(anime_data["description_en"])
    anime = Anime(**anime_data, added_by=pending.proposed_by)
    db.add(anime)
    pending.status = "approved"
    db.commit()
    db.refresh(anime)
    db.add(Notification(
        user_id=pending.proposed_by, type="approval",
        title_fr="Proposition acceptée ✓", title_en="Proposal approved ✓",
        body_fr=f"Ton animé \"{anime.title}\" a été ajouté au catalogue.",
        body_en=f"Your anime \"{anime.title}\" has been added to the catalogue.",
        link=f"/catalogue.html?id={anime.id}"
    ))
    db.commit()
    return {"message": "Proposition approuvée", "anime_id": anime.id}


@app.post("/admin/pending/{pending_id}/reject")
def reject_pending(pending_id: int, data: RejectSchema, current_user=Depends(require_admin), db: Session = Depends(get_db)):
    pending = db.query(AnimePending).filter(AnimePending.id == pending_id).first()
    if not pending:
        raise HTTPException(status_code=404, detail="Proposition introuvable")
    pending.status     = "rejected"
    pending.admin_note = json.dumps({"fr": data.note_fr, "en": data.note_en})
    db.add(Notification(
        user_id=pending.proposed_by, type="approval",
        title_fr="Proposition refusée", title_en="Proposal rejected",
        body_fr=data.note_fr, body_en=data.note_en,
    ))
    db.commit()
    return {"message": "Proposition refusée"}


@app.get("/admin/reports")
def get_reports(current_user=Depends(require_admin), db: Session = Depends(get_db)):
    reports = db.query(AnimeReport).filter(AnimeReport.status == "pending").all()
    return [
        {"id": r.id, "anime_id": r.anime_id, "reported_by": r.reported_by,
         "message": r.message, "created_at": r.created_at.isoformat() if r.created_at else None}
        for r in reports
    ]


@app.put("/admin/reports/{report_id}/resolve")
def resolve_report(report_id: int, data: RejectSchema, current_user=Depends(require_admin), db: Session = Depends(get_db)):
    report = db.query(AnimeReport).filter(AnimeReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Signalement introuvable")
    report.status         = "resolved"
    report.admin_response = json.dumps({"fr": data.note_fr, "en": data.note_en})
    db.add(Notification(
        user_id=report.reported_by, type="report_resolved",
        title_fr="Signalement traité", title_en="Report resolved",
        body_fr=data.note_fr, body_en=data.note_en,
    ))
    db.commit()
    return {"message": "Signalement résolu"}


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES — SAISON TRACKING
# ══════════════════════════════════════════════════════════════════════════════

class SeasonTrackingSchema(BaseModel):
    season_number:    int
    episodes_watched: Optional[int] = None
    episodes_total:   Optional[int] = None
    status:           Optional[str] = None
    watch_start:      Optional[str] = None
    watch_end:        Optional[str] = None

@app.get("/watchlists/{watchlist_id}/entries/{entry_id}/seasons")
def get_seasons(watchlist_id: int, entry_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == current_user.id).first():
        raise HTTPException(status_code=404, detail="Watchlist introuvable")
    seasons = db.query(WatchlistSeasonTracking).filter(WatchlistSeasonTracking.entry_id == entry_id).order_by(WatchlistSeasonTracking.season_number).all()
    return [
        {
            "id":               s.id,
            "entry_id":         s.entry_id,
            "season_number":    s.season_number,
            "episodes_watched": s.episodes_watched,
            "episodes_total":   s.episodes_total,
            "status":           s.status,
            "watch_start":      s.watch_start,
            "watch_end":        s.watch_end,
        }
        for s in seasons
    ]

@app.post("/watchlists/{watchlist_id}/entries/{entry_id}/seasons")
def add_season(watchlist_id: int, entry_id: int, data: SeasonTrackingSchema, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == current_user.id).first():
        raise HTTPException(status_code=404, detail="Watchlist introuvable")
    existing = db.query(WatchlistSeasonTracking).filter(
        WatchlistSeasonTracking.entry_id == entry_id,
        WatchlistSeasonTracking.season_number == data.season_number
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Saison déjà existante")
    season = WatchlistSeasonTracking(entry_id=entry_id, **data.model_dump())
    db.add(season)
    db.commit()
    db.refresh(season)
    return {"message": "Saison ajoutée", "id": season.id}

@app.put("/watchlists/{watchlist_id}/entries/{entry_id}/seasons/{season_id}")
def update_season(watchlist_id: int, entry_id: int, season_id: int, data: SeasonTrackingSchema, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == current_user.id).first():
        raise HTTPException(status_code=404, detail="Watchlist introuvable")
    season = db.query(WatchlistSeasonTracking).filter(WatchlistSeasonTracking.id == season_id, WatchlistSeasonTracking.entry_id == entry_id).first()
    if not season:
        raise HTTPException(status_code=404, detail="Saison introuvable")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(season, field, value)
    db.commit()
    return {"message": "Saison mise à jour"}

@app.delete("/watchlists/{watchlist_id}/entries/{entry_id}/seasons/{season_id}")
def delete_season(watchlist_id: int, entry_id: int, season_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == current_user.id).first():
        raise HTTPException(status_code=404, detail="Watchlist introuvable")
    season = db.query(WatchlistSeasonTracking).filter(WatchlistSeasonTracking.id == season_id, WatchlistSeasonTracking.entry_id == entry_id).first()
    if not season:
        raise HTTPException(status_code=404, detail="Saison introuvable")
    db.delete(season)
    db.commit()
    return {"message": "Saison supprimée"}


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES — NOTIFICATION PREFS
# ══════════════════════════════════════════════════════════════════════════════

class NotifPrefsSchema(BaseModel):
    lang:              Optional[str]  = None
    notify_new_season: Optional[bool] = None
    notify_new_anime:  Optional[bool] = None
    notify_admin:      Optional[bool] = None
    notify_email:      Optional[bool] = None
    notify_inapp:      Optional[bool] = None

@app.get("/notifications/prefs")
def get_notif_prefs(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    prefs = db.query(UserNotificationPrefs).filter(UserNotificationPrefs.user_id == current_user.id).first()
    if not prefs:
        # Crée les prefs par défaut si elles n'existent pas
        prefs = UserNotificationPrefs(user_id=current_user.id)
        db.add(prefs)
        db.commit()
    return {
        "lang":              prefs.lang,
        "notify_new_season": prefs.notify_new_season,
        "notify_new_anime":  prefs.notify_new_anime,
        "notify_admin":      prefs.notify_admin,
        "notify_email":      prefs.notify_email,
        "notify_inapp":      prefs.notify_inapp,
    }

@app.put("/notifications/prefs")
def update_notif_prefs(data: NotifPrefsSchema, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    prefs = db.query(UserNotificationPrefs).filter(UserNotificationPrefs.user_id == current_user.id).first()
    if not prefs:
        prefs = UserNotificationPrefs(user_id=current_user.id)
        db.add(prefs)
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(prefs, field, value)
    db.commit()
    return {"message": "Préférences mises à jour"}


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES — ONBOARDING
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/onboarding/done")
def mark_onboarding_done(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.onboarding_done = True
    db.commit()
    return {"message": "Onboarding terminé"}

@app.get("/onboarding/status")
def get_onboarding_status(current_user=Depends(get_current_user)):
    return {"onboarding_done": current_user.onboarding_done}


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES — RANDOM ANIME ("Quoi regarder ?")
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/anime/random")
def get_random_anime(
    mode: str = Query("random", description="'random' ou 'best'"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Récupère tous les anime_id déjà dans les watchlists du user
    user_watchlists = db.query(Watchlist).filter(Watchlist.user_id == current_user.id).all()
    user_anime_ids = set()
    for w in user_watchlists:
        entries = db.query(WatchlistEntry.anime_id).filter(WatchlistEntry.watchlist_id == w.id).all()
        user_anime_ids.update(e.anime_id for e in entries)

    # Catalogue filtré — exclut ce que le user a déjà
    query = db.query(Anime).filter(Anime.is_archived == False)
    if user_anime_ids:
        query = query.filter(Anime.id.notin_(user_anime_ids))

    animes = query.all()
    if not animes:
        raise HTTPException(status_code=404, detail="Aucun animé disponible")

    if mode == "best":
        # Trie par score moyen des entrées en BDD
        def avg_score(anime):
            scores = db.query(WatchlistEntry.score).filter(
                WatchlistEntry.anime_id == anime.id,
                WatchlistEntry.score != None
            ).all()
            if not scores:
                return 0
            return sum(s.score for s in scores) / len(scores)
        animes_sorted = sorted(animes, key=avg_score, reverse=True)
        chosen = animes_sorted[0] if animes_sorted else random.choice(animes)
    else:
        chosen = random.choice(animes)

    return anime_to_dict(chosen)


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES — EXPORT CSV
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/watchlists/{watchlist_id}/export")
def export_watchlist_csv(watchlist_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    watchlist = db.query(Watchlist).filter(Watchlist.id == watchlist_id, Watchlist.user_id == current_user.id).first()
    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist introuvable")

    entries = db.query(WatchlistEntry).filter(WatchlistEntry.watchlist_id == watchlist_id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "titre", "titre_en", "statut", "score", "episodes_vus", "saisons_vues",
        "debut", "fin", "plateforme", "favori", "a_revoir", "epingle",
        "avis_perso", "infos_sup", "tags", "date_ajout"
    ])
    for e in entries:
        anime = db.query(Anime).filter(Anime.id == e.anime_id).first()
        writer.writerow([
            anime.title if anime else "",
            anime.title_en if anime else "",
            e.watch_status or "",
            e.score or "",
            e.episodes_watched or "",
            e.seasons_watched or "",
            e.watch_start or "",
            e.watch_end or "",
            e.platform or "",
            "oui" if e.is_favorite else "non",
            "oui" if e.is_to_rewatch else "non",
            "oui" if e.is_pinned else "non",
            e.personal_review or "",
            e.extra_info or "",
            e.custom_tags or "",
            e.created_at.isoformat() if e.created_at else "",
        ])

    output.seek(0)
    filename = f"watchlist_{watchlist.name.replace(' ', '_')}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),  # utf-8-sig = compatible Excel
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.get("/admin/anime/export")
def export_catalogue_csv(current_user=Depends(require_admin), db: Session = Depends(get_db)):
    animes = db.query(Anime).filter(Anime.is_archived == False).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "titre", "titre_en", "type", "statut", "studio", "auteur",
        "saisons", "episodes", "duree_ep", "debut", "fin",
        "genres", "plateformes", "anilist_id", "ajoute_le"
    ])
    for a in animes:
        writer.writerow([
            a.id, a.title, a.title_en or "", a.type or "", a.anime_status or "",
            a.studio or "", a.author or "", a.seasons_total or "",
            a.episodes_total or "", a.episode_duration or "",
            a.air_start or "", a.air_end or "",
            a.genres or "", a.platforms or "",
            a.anilist_id or "",
            a.created_at.isoformat() if a.created_at else "",
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=catalogue.csv"}
    )


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES — CHANGELOG
# ══════════════════════════════════════════════════════════════════════════════

class ChangelogCreateSchema(BaseModel):
    title_fr: str
    title_en: str
    body_fr:  str
    body_en:  str

@app.get("/changelog")
def get_changelog(db: Session = Depends(get_db)):
    entries = db.query(Changelog).order_by(Changelog.published_at.desc()).limit(20).all()
    return [
        {
            "id":           e.id,
            "title_fr":     e.title_fr,
            "title_en":     e.title_en,
            "body_fr":      e.body_fr,
            "body_en":      e.body_en,
            "published_at": e.published_at.isoformat() if e.published_at else None,
        }
        for e in entries
    ]

@app.post("/changelog")
def create_changelog(data: ChangelogCreateSchema, current_user=Depends(require_admin), db: Session = Depends(get_db)):
    entry = Changelog(**data.model_dump(), published_by=current_user.id)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"message": "Entrée changelog créée", "id": entry.id}


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES — ADMIN BROADCASTS
# ══════════════════════════════════════════════════════════════════════════════

class BroadcastSchema(BaseModel):
    title_fr:     str
    title_en:     str
    body_fr:      str
    body_en:      str

@app.post("/admin/broadcast")
def send_broadcast(data: BroadcastSchema, current_user=Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).all()
    notifs = []
    for user in users:
        prefs = db.query(UserNotificationPrefs).filter(UserNotificationPrefs.user_id == user.id).first()
        if prefs and not prefs.notify_admin:
            continue
        notifs.append(Notification(
            user_id=user.id, type="admin_message",
            title_fr=data.title_fr, title_en=data.title_en,
            body_fr=data.body_fr,   body_en=data.body_en,
        ))
    db.add_all(notifs)
    broadcast = AdminBroadcast(
        title_fr=data.title_fr, title_en=data.title_en,
        body_fr=data.body_fr,   body_en=data.body_en,
        sent_at=datetime.utcnow(), sent_by=current_user.id,
        recipient_count=len(notifs)
    )
    db.add(broadcast)
    db.commit()
    return {"message": f"Broadcast envoyé à {len(notifs)} utilisateurs"}

@app.get("/admin/broadcasts")
def get_broadcasts(current_user=Depends(require_admin), db: Session = Depends(get_db)):
    broadcasts = db.query(AdminBroadcast).order_by(AdminBroadcast.sent_at.desc()).limit(20).all()
    return [
        {
            "id":              b.id,
            "title_fr":        b.title_fr,
            "title_en":        b.title_en,
            "sent_at":         b.sent_at.isoformat() if b.sent_at else None,
            "recipient_count": b.recipient_count,
        }
        for b in broadcasts
    ]


# ══════════════════════════════════════════════════════════════════════════════
#  JOB ANILIST QUOTIDIEN — mise à jour animés "airing"
# ══════════════════════════════════════════════════════════════════════════════

async def refresh_airing_animes():
    """
    Tourne en background au démarrage puis toutes les 24h.
    Met à jour episodes_total et anime_status des animés 'airing' depuis AniList.
    Respecte la limite de 90 req/min (pause entre chaque appel).
    """
    await asyncio.sleep(30)  # Attend 30s après le démarrage pour ne pas bloquer
    while True:
        db = SessionLocal()
        try:
            airing = db.query(Anime).filter(
                Anime.anime_status == "airing",
                Anime.anilist_id != None,
                Anime.is_archived == False
            ).all()

            gql_query = """
            query ($id: Int) {
                Media(id: $id, type: ANIME) {
                    status
                    episodes
                    nextAiringEpisode { episode }
                }
            }
            """
            async with httpx.AsyncClient() as client:
                for anime in airing:
                    try:
                        resp = await client.post(
                            "https://graphql.anilist.co",
                            json={"query": gql_query, "variables": {"id": anime.anilist_id}},
                            timeout=10.0
                        )
                        data = resp.json().get("data", {}).get("Media", {})
                        if data:
                            new_status   = data.get("status", "").lower()
                            new_episodes = data.get("episodes")
                            if new_status and new_status != anime.anime_status:
                                anime.anime_status = new_status
                            if new_episodes and new_episodes != anime.episodes_total:
                                anime.episodes_total = new_episodes
                        db.commit()
                        await asyncio.sleep(0.7)  # ~85 req/min max → respecte la limite AniList
                    except Exception:
                        continue
        except Exception:
            pass
        finally:
            db.close()

        await asyncio.sleep(86400)  # 24h


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(refresh_airing_animes())