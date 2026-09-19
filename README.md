CollegeTrends Backend

Backend services powering CollegeTrends, a student-focused social platform for student profiles, campus content, social interactions, media sharing, and personalized discovery.

Overview

CollegeTrends Backend provides the REST API and server-side infrastructure for the CollegeTrends platform.

The backend handles user authentication, profile management, social relationships, feed generation, post creation, media uploads, comments, reactions, voting, bookmarks, and database operations.

The application is implemented with Flask and PostgreSQL and uses token-based authentication to protect authenticated resources.

Core Capabilities

Authentication

- User registration
- User login
- JWT-based authentication
- Protected API endpoints
- Authenticated user context
- Password hashing with bcrypt
- Password changes

The registration system captures student-oriented information including username, email, full name, university, and course.

Student Profiles

The API supports:

- Profile retrieval
- Profile updates
- Username validation
- University and course information
- Biography
- Avatar management
- Profile privacy
- Verification status
- Profile statistics

Social Feed

The backend generates an authenticated student feed containing post information, author information, engagement metrics, and student context.

Posts

Authenticated users can:

- Create posts
- Attach media
- Add captions
- Add tags
- Retrieve individual posts
- Delete their posts

The API stores post metadata, media information, engagement counts, and author information.

Engagement

The backend implements multiple interaction systems:

- Likes
- Comments
- Upvotes
- Downvotes
- Bookmarks

Posts expose engagement state such as like status, bookmark status, vote state, and interaction counts.

Media Uploads

Cloudinary is used for image uploads, including user avatars and post media. The backend uploads media and stores the resulting secure URL in PostgreSQL.

API Structure

Representative endpoints include:

POST   /api/register
POST   /api/login
GET    /api/me

GET    /api/users/<user_id>
PATCH  /api/users/me
POST   /api/users/me/password
POST   /api/users/me/avatar

GET    /api/feed

POST   /api/posts
GET    /api/posts/<post_id>
DELETE /api/posts/<post_id>

POST   /api/posts/<post_id>/like
POST   /api/posts/<post_id>/vote

POST   /api/posts/<post_id>/bookmark
GET    /api/bookmarks

GET    /health

The API uses authenticated route protection for user-specific operations.

Authentication Architecture

Client
  │
  │ Credentials
  ▼
POST /api/login
  │
  ▼
Credential verification
  │
  ▼
JWT issued
  │
  ▼
Authenticated API requests
  │
  │ Bearer token
  ▼
token_required middleware
  │
  ▼
Protected resource

Protected endpoints use a token-based authentication layer to identify the current user before executing authenticated operations.

Technology Stack

- Python
- Flask
- PostgreSQL
- psycopg2
- JWT
- bcrypt
- Cloudinary
- Flask-CORS
- REST APIs
- Git & GitHub

The source imports Flask, Flask-CORS, psycopg2, JWT, bcrypt, and Cloudinary directly in the application.

Architecture

┌───────────────────────┐
│   CollegeTrends UI   │
│ HTML / CSS / JS       │
└───────────┬───────────┘
            │
            │ HTTP / JSON
            ▼
┌───────────────────────┐
│      Flask API        │
│ Authentication        │
│ Profiles              │
│ Feed                  │
│ Posts                 │
│ Engagement            │
└───────┬─────────┬─────┘
        │         │
        ▼         ▼
 PostgreSQL   Cloudinary
  Database       Media

Database

The backend uses PostgreSQL as its relational data store.

The application maintains separate database entities for users, posts, follows, comments, likes, votes, and bookmarks, allowing social relationships and engagement data to be represented independently.

Security

Authentication uses JWT tokens, while passwords are hashed using bcrypt before storage.



Clone the repository:

git clone <repository-url>
cd CollegeTrends_Server

Install dependencies:

pip install -r requirements.txt

Configure the required environment variables for:

DATABASE
CLOUDINARY
JWT
APPLICATION

Then start the Flask application:

python server.py

Health Check

The backend exposes:

GET /health

A successful response confirms that the API process is running.

Project Status

Backend MVP / Active Project

CollegeTrends Backend is maintained as the server-side component of the CollegeTrends platform.

Related Project

The corresponding CollegeTrends frontend is maintained separately.