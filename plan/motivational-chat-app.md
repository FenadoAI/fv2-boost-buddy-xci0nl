# Motivational Chat App - Implementation Plan

## Overview
Build a motivational chat web app with AI-powered positive encouragement and daily quotes.

## Backend Tasks
1. **API Endpoints** (server.py)
   - `POST /api/chat/motivational` - Send message, get AI response
   - `GET /api/chat/history` - Retrieve user's chat history
   - `GET /api/daily-quote` - Get daily motivational quote
   - `POST /api/auth/signup` - User registration
   - `POST /api/auth/login` - User authentication

2. **Database Schema** (MongoDB)
   - Collection: `users` (existing) - store user credentials
   - Collection: `chat_messages` - store conversation history
     - user_id, message, response, timestamp, quote_of_day

3. **AI Agent Configuration**
   - Use ChatAgent with motivational system prompt
   - Configure for supportive, encouraging responses
   - Include daily quote generation capability

## Frontend Tasks
1. **Authentication Pages**
   - Login page
   - Signup page
   - JWT token management

2. **Main Chat Interface**
   - Single-view chat screen
   - Message display (user + AI)
   - Input box for typing
   - Daily quote display section
   - Chat history persistence

3. **Navigation**
   - Header with logout
   - Link to chat from homepage

## Implementation Order
1. Backend APIs (test each endpoint)
2. Frontend authentication flow
3. Frontend chat interface
4. Integration testing
5. Build and deploy

## AI Model
- Use `gemini-2.5-flash` for fast, friendly responses
- System prompt: Focus on motivation, positivity, encouragement
