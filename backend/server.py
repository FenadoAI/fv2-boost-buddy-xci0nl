"""FastAPI server exposing AI agent endpoints."""

import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware

from ai_agents.agents import AgentConfig, ChatAgent, SearchAgent


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"

security = HTTPBearer()


class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StatusCheckCreate(BaseModel):
    client_name: str


class ChatRequest(BaseModel):
    message: str
    agent_type: str = "chat"
    context: Optional[dict] = None


class ChatResponse(BaseModel):
    success: bool
    response: str
    agent_type: str
    capabilities: List[str]
    metadata: dict = Field(default_factory=dict)
    error: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    max_results: int = 5


class SearchResponse(BaseModel):
    success: bool
    query: str
    summary: str
    search_results: Optional[dict] = None
    sources_count: int
    error: Optional[str] = None


class UserSignup(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    username: Optional[str] = None
    message: Optional[str] = None


class MotivationalChatRequest(BaseModel):
    message: str


class MotivationalChatResponse(BaseModel):
    success: bool
    response: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[str] = None


class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    message: str
    response: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DailyQuoteResponse(BaseModel):
    success: bool
    quote: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[str] = None


def _ensure_db(request: Request):
    try:
        return request.app.state.db
    except AttributeError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=503, detail="Database not ready") from exc


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def _create_token(user_id: str, username: str) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.now(timezone.utc).timestamp() + 86400 * 7,  # 7 days
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def _get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), request: Request = None):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def _get_agent_cache(request: Request) -> Dict[str, object]:
    if not hasattr(request.app.state, "agent_cache"):
        request.app.state.agent_cache = {}
    return request.app.state.agent_cache


async def _get_or_create_agent(request: Request, agent_type: str):
    cache = _get_agent_cache(request)
    if agent_type in cache:
        return cache[agent_type]

    config: AgentConfig = request.app.state.agent_config

    if agent_type == "search":
        cache[agent_type] = SearchAgent(config)
    elif agent_type == "chat":
        cache[agent_type] = ChatAgent(config)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown agent type '{agent_type}'")

    return cache[agent_type]


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv(ROOT_DIR / ".env")

    mongo_url = os.getenv("MONGO_URL")
    db_name = os.getenv("DB_NAME")

    if not mongo_url or not db_name:
        missing = [name for name, value in {"MONGO_URL": mongo_url, "DB_NAME": db_name}.items() if not value]
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    client = AsyncIOMotorClient(mongo_url)

    try:
        app.state.mongo_client = client
        app.state.db = client[db_name]
        app.state.agent_config = AgentConfig()
        app.state.agent_cache = {}
        logger.info("AI Agents API starting up")
        yield
    finally:
        client.close()
        logger.info("AI Agents API shutdown complete")


app = FastAPI(
    title="AI Agents API",
    description="Minimal AI Agents API with LangGraph and MCP support",
    lifespan=lifespan,
)

api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"message": "Hello World"}


@api_router.post("/auth/signup", response_model=AuthResponse)
async def signup(user: UserSignup, request: Request):
    try:
        db = _ensure_db(request)

        # Check if user exists
        existing_user = await db.users.find_one({"username": user.username})
        if existing_user:
            return AuthResponse(success=False, message="Username already exists")

        existing_email = await db.users.find_one({"email": user.email})
        if existing_email:
            return AuthResponse(success=False, message="Email already exists")

        # Create user
        user_id = str(uuid.uuid4())
        user_doc = {
            "id": user_id,
            "username": user.username,
            "email": user.email,
            "password": _hash_password(user.password),
            "created_at": datetime.now(timezone.utc),
        }
        await db.users.insert_one(user_doc)

        # Generate token
        token = _create_token(user_id, user.username)

        return AuthResponse(success=True, token=token, username=user.username, message="Account created successfully")
    except Exception as exc:
        logger.exception("Error in signup")
        return AuthResponse(success=False, message=str(exc))


@api_router.post("/auth/login", response_model=AuthResponse)
async def login(user: UserLogin, request: Request):
    try:
        db = _ensure_db(request)

        # Find user
        user_doc = await db.users.find_one({"username": user.username})
        if not user_doc or not _verify_password(user.password, user_doc["password"]):
            return AuthResponse(success=False, message="Invalid username or password")

        # Generate token
        token = _create_token(user_doc["id"], user_doc["username"])

        return AuthResponse(success=True, token=token, username=user_doc["username"], message="Login successful")
    except Exception as exc:
        logger.exception("Error in login")
        return AuthResponse(success=False, message=str(exc))


@api_router.post("/chat/motivational", response_model=MotivationalChatResponse)
async def motivational_chat(chat_req: MotivationalChatRequest, request: Request, current_user: dict = Depends(_get_current_user)):
    try:
        db = _ensure_db(request)

        # Create motivational chat agent
        agent = await _get_or_create_agent(request, "chat")

        # System prompt for motivation
        motivational_prompt = f"""You are a supportive and encouraging AI companion designed to provide motivation and positivity.
Your goal is to uplift users with positive encouragement, practical advice, and daily motivation.
Be empathetic, understanding, and always maintain an optimistic yet realistic tone.
Keep responses concise but meaningful.

User message: {chat_req.message}"""

        # Get AI response
        result = await agent.execute(motivational_prompt)

        if not result.success:
            return MotivationalChatResponse(success=False, response="", error=result.error)

        # Save to chat history
        chat_message = ChatMessage(
            user_id=current_user["user_id"],
            message=chat_req.message,
            response=result.content,
        )
        await db.chat_messages.insert_one(chat_message.model_dump())

        return MotivationalChatResponse(success=True, response=result.content)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error in motivational chat")
        return MotivationalChatResponse(success=False, response="", error=str(exc))


@api_router.get("/chat/history")
async def get_chat_history(request: Request, current_user: dict = Depends(_get_current_user)):
    try:
        db = _ensure_db(request)

        messages = await db.chat_messages.find(
            {"user_id": current_user["user_id"]}
        ).sort("timestamp", -1).limit(50).to_list(50)

        return {"success": True, "messages": [ChatMessage(**msg) for msg in messages]}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error getting chat history")
        return {"success": False, "error": str(exc)}


@api_router.get("/daily-quote", response_model=DailyQuoteResponse)
async def get_daily_quote(request: Request, current_user: dict = Depends(_get_current_user)):
    try:
        agent = await _get_or_create_agent(request, "chat")

        quote_prompt = """Generate a single inspiring and motivational quote.
It should be uplifting, positive, and encouraging.
Format: Just the quote itself, no attribution needed. Keep it concise and impactful."""

        result = await agent.execute(quote_prompt)

        if not result.success:
            return DailyQuoteResponse(success=False, quote="", error=result.error)

        return DailyQuoteResponse(success=True, quote=result.content)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error generating daily quote")
        return DailyQuoteResponse(success=False, quote="", error=str(exc))


@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate, request: Request):
    db = _ensure_db(request)
    status_obj = StatusCheck(**input.model_dump())
    await db.status_checks.insert_one(status_obj.model_dump())
    return status_obj


@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks(request: Request):
    db = _ensure_db(request)
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]


@api_router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(chat_request: ChatRequest, request: Request):
    try:
        agent = await _get_or_create_agent(request, chat_request.agent_type)
        response = await agent.execute(chat_request.message)

        return ChatResponse(
            success=response.success,
            response=response.content,
            agent_type=chat_request.agent_type,
            capabilities=agent.get_capabilities(),
            metadata=response.metadata,
            error=response.error,
        )
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Error in chat endpoint")
        return ChatResponse(
            success=False,
            response="",
            agent_type=chat_request.agent_type,
            capabilities=[],
            error=str(exc),
        )


@api_router.post("/search", response_model=SearchResponse)
async def search_and_summarize(search_request: SearchRequest, request: Request):
    try:
        search_agent = await _get_or_create_agent(request, "search")
        search_prompt = (
            f"Search for information about: {search_request.query}. "
            "Provide a comprehensive summary with key findings."
        )
        result = await search_agent.execute(search_prompt, use_tools=True)

        if result.success:
            metadata = result.metadata or {}
            return SearchResponse(
                success=True,
                query=search_request.query,
                summary=result.content,
                search_results=metadata,
                sources_count=int(metadata.get("tool_run_count", metadata.get("tools_used", 0)) or 0),
            )

        return SearchResponse(
            success=False,
            query=search_request.query,
            summary="",
            sources_count=0,
            error=result.error,
        )
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Error in search endpoint")
        return SearchResponse(
            success=False,
            query=search_request.query,
            summary="",
            sources_count=0,
            error=str(exc),
        )


@api_router.get("/agents/capabilities")
async def get_agent_capabilities(request: Request):
    try:
        search_agent = await _get_or_create_agent(request, "search")
        chat_agent = await _get_or_create_agent(request, "chat")

        return {
            "success": True,
            "capabilities": {
                "search_agent": search_agent.get_capabilities(),
                "chat_agent": chat_agent.get_capabilities(),
            },
        }
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Error getting capabilities")
        return {"success": False, "error": str(exc)}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
