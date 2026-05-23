# AgroMind AI

AI-powered agriculture platform with crop disease detection, AI recommendations,
marketplace, secure payments, admin operations, and future AI RAG assistant.

## Tech Stack

Frontend:
- React
- Vite
- TailwindCSS
- Axios
- React Router
- Context API / Zustand

Backend:
- FastAPI
- MongoDB
- Motor async driver
- JWT Authentication
- Razorpay
- TensorFlow
- YOLO

Deployment:
- Frontend: Vercel
- Backend: Render
- Database: MongoDB Atlas
- Email: Resend API, not Gmail SMTP

## Core Rules

- Backend routes must be async.
- Use Pydantic validation.
- Prefer service and repository boundaries as the app grows.
- Use centralized error handling and response formatting.
- Use environment variables only.
- Never hardcode secrets.
- Frontend must be responsive, mobile-first, and use a centralized axios client.
- Protected routes, admin dashboard, and loading/error states are required.

## Roles

Only two roles exist: `farmer` and `admin`.

Farmers can register/login, upload crop images, use AI disease detection, view
recommendations, buy marketplace products, manage profile, view orders, use cart
and wishlist, and pay with Razorpay. Farmers cannot access admin routes, manage
products globally, manage users, or access analytics.

Admins have full system access: manage products, orders, users, inventory,
analytics, dashboard, payments, and manual refunds. Admin routes must be
protected.

## Admin Registration

Admin accounts are not public. To create an admin, the user must provide a valid
OTP and the `ADMIN_REGISTER_SECRET` from the environment.

```env
ADMIN_REGISTER_SECRET=your_secret
```

Normal users can never become admin without the secret.

## Authentication

- JWT authentication
- Secure HTTP-only cookies or bearer tokens
- bcrypt password hashing
- Access and refresh tokens
- Role-based route protection
- Email verification
- OTP verification
- Rate limiting

## OTP And Email

Do not use Gmail SMTP. Use Resend API because SMTP is unreliable on Render.

```env
RESEND_API_KEY=
EMAIL_FROM=
```

OTP must support async sending, retries, expiry, and rate limiting.

## Razorpay

Payment flow:
1. Validate stock.
2. Create Razorpay order.
3. Open Razorpay checkout in the frontend.
4. Verify Razorpay signature in the backend.
5. Only after successful verification, create order, reduce stock, and clear cart.

Never reduce stock before payment success.

## Marketplace

- If stock is less than or equal to zero, disable Buy Now and checkout.
- Show Out of Stock.
- Validate stock before checkout.
- Remove invalid cart items automatically.
- Prevent duplicate cart issues.
- Order statuses: `pending`, `paid`, `processing`, `shipped`, `delivered`, `cancelled`.

## Admin Dashboard

Required areas:
- Analytics: total users, farmers, orders, revenue, low stock products, AI predictions count
- Product management: add, edit, delete, update stock, upload images
- User management: view, delete, block, unblock, change roles as admin only
- Order management: view, update status, search/filter
- AI analytics: diseases, crops, prediction history stats

## CORS And Security

- Production CORS must be strict.
- Allow localhost only during development.
- Allow the Vercel frontend domain in production.
- Remove LAN IPs from production.
- Add TrustedHostMiddleware, rate limiting, request validation, secure cookies,
  CSRF protection, and security headers.

## Deployment

Render backend must start without errors, expose a health endpoint, connect to
MongoDB, auto-load models, and validate the environment at startup.

Vercel frontend must use the production API URL, refresh auth properly, and
persist auth.

## AI

Maintain TensorFlow disease classification, YOLO detection, GradCAM, and the
recommendation engine. Supported crops are `tomato`, `mango`, and `coconut`.

## Future RAG

Prepare architecture for LangChain, ChromaDB, RAG pipelines, AI chatbot,
multilingual support, farmer Q&A, government scheme assistant, fertilizer
guidance, weather-aware recommendations, voice, Hindi, and Marathi.

## Database

Collections:
- users
- products
- carts
- orders
- payments
- prediction_history
- email_otps

Indexes:
- unique email index
- product indexes
- order indexes
- TTL index for OTP expiry

## Logging

Implement structured logs, error logs, payment logs, and AI prediction logs.
Never expose secrets in logs.

## Required Environment Variables

```env
MONGO_URL=
JWT_SECRET=
JWT_REFRESH_SECRET=
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RESEND_API_KEY=
EMAIL_FROM=
ADMIN_REGISTER_SECRET=
FRONTEND_URL=
BACKEND_URL=
MODEL_PATH_TOMATO=
MODEL_PATH_MANGO=
MODEL_PATH_COCONUT=
```
