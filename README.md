# 🪑 FurniCraft – Furniture E-commerce Platform

FurniCraft is a **production-oriented furniture e-commerce platform** built using **Django** and **Tailwind CSS**.  
The project replicates real-world e-commerce workflows including secure OTP authentication, modular offer systems, order lifecycle management, wallet-based refunds, and a fully custom admin panel.

The primary focus of this project is **business logic correctness, clean architecture, and scalable system design**, rather than simple CRUD functionality.

---

## 🚀 Key Highlights

- OTP-based email authentication and verification
- Modular offer system (category, product, referral)
- HTMX-powered dynamic UI interactions (no full page reloads)
- Custom wallet system with transaction history
- Order cancellation and return workflows with refund handling
- Secure checkout with Razorpay, Wallet, and Cash on Delivery
- Fully custom admin panel (not Django default admin)
- Stock-aware cart and checkout validation

---

## 🧠 System Architecture Overview

### Frontend
- HTML
- Tailwind CSS
- JavaScript
- HTMX

### Backend
- Django (MVT Architecture)
- Django ORM
- Custom admin panel

### Database
- PostgreSQL

### Authentication
- Django authentication system
- OTP-based verification

### Payments
- Razorpay
- Wallet
- Cash on Delivery (COD)

---

### Example Flow – Order & Refund

1. User places an order using COD / Razorpay / Wallet
2. Stock is validated during checkout
3. Order items move through status lifecycle
4. Cancellation or return triggers refund calculation
5. Refund amount is credited to the user wallet
6. All wallet transactions are logged for traceability

---

## 👤 User Features

### Authentication & Profile
- User registration with OTP email verification
- Secure login and logout
- OTP-based email change
- Profile and address management

### Shopping Experience
- Browse products by category
- Product variants with images and pricing
- Category, product, and referral offers
- Wishlist management
- Cart management with real-time stock validation
- Dynamic UI updates using HTMX

### Checkout & Orders
- Multiple payment methods: Wallet, Razorpay, COD
- Order placement and order history
- Order tracking with status updates
- Order cancellation rules
- Return request and approval workflow
- Wallet refunds with transaction history

### Reviews & Ratings
- Verified-purchase review system
- One review per product per user
- Rating and textual feedback
- Average rating calculation per product
- Admin moderation support

---

## 🛠️ Admin Features

### Dashboard
- Overview of orders, users, and products
- Top-selling products and categories

### Management Modules
- Category, product, and variant management
- Offer management (category, product, referral)
- Banner and discount management
- Inventory and stock control

### Orders & Finance
- Order processing and status updates
- Return approvals and refunds
- Wallet credit and debit handling
- Secure admin-only actions

---

## 🧰 Tech Stack

### Frontend
- HTML
- Tailwind CSS
- JavaScript
- HTMX

### Backend
- Django
- Django ORM

### Database
- PostgreSQL

### Payments
- Razorpay
- Cash on Delivery
- Custom Wallet System

---

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.10+
- PostgreSQL
- Git
- Virtual Environment (venv)

---

### Clone Repository
```bash```
git clone https://github.com/Reyhanakm/E-commerce-FurniCraft.git
cd E-commerce-FurniCraft


## Virtual Environment

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt


## Environment Variables

Create a .env file in the project root.

SECRET_KEY=
DEBUG=
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=

### Database & Server

python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic
python manage.py runserver

## Security Considerations

OTPs are time-bound and single-use

Sensitive credentials are stored in environment variables

OTP values are never logged

Admin routes are strictly protected

Wallet and refund operations use atomic transactions

### Future Enhancements

Advanced filtering and sorting

Product comparison

Coupon system

Performance optimization and caching

### Author

Reyhana K M

Built as part of the Brototype Full-Stack Learning Program.

### License

Copyright © 2026 Reyhana K M

This project is licensed under the MIT License.

