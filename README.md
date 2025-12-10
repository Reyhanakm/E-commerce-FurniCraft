# FurniCraft – Furniture E-commerce Website

FurniCraft is a full-featured furniture e-commerce platform built with Django, styled using Tailwind CSS, and powered by PostgreSQL.
The application includes all essential modern e-commerce modules such as product variants, category and product offers, referral offers, 
secure OTP authentication, wishlist, cart, orders, returns, and a complete custom admin panel. HTMX is used to enhance UI interactions without full page reloads.

## User Features
------------------

### Authentication and User Management
----------------------------------------

* User registration with OTP email verification
* Secure email change with OTP
* User login and logout
* User profile management
* Address management (add, edit, delete)

### Shopping Experience
-----------------------

* Browse products by category
* Category offers, product offers, and referral offers
* Product detail page with images, descriptions, and variants
* Wishlist management
* Add to cart, update quantity, remove items
* Real-time cart stock validation
* Asynchronous interactions using HTMX (for faster UI updates)
* Custom wallet system with transaction history

### Checkout and Orders
------------------------

* Checkout with Cash on Delivery, Razorpay, and Wallet
* Order placement and order history
* Order tracking with status updates
* Order cancellation
* Order return requests


## Admin Features
------------------

### Admin Dashboard
--------------------

* Overview of orders, products, and users
* Top-selling products and categories 


### Management Modules
-----------------------

* Category management
* Product and Variant CRUD operations
* Offer management (category, product, referral)
* Banner management
* Discount handling
* Inventory and stock management

### Order and Customer Handling
-------------------------------

* View and process orders
* Update order status
* Manage returns and refunds
* Wallet credit and debit management


## Tech Stack
--------------

### Frontend
-------------

* HTML
* Tailwind CSS
* JavaScript
* HTMX (for partial updates and dynamic interactions)

### Backend
-----------

* Django
* Django ORM
* Custom admin panel

### Database
------------

* PostgreSQL

### Authentication
-------------------

* Django authentication system
* OTP-based verification

### Payments
--------------

* Razorpay
* Cash on Delivery
* Custom wallet system


## Future Enhancements
-----------------------

* Advanced filtering and sorting
* Review and rating system
* Coupon system
* Product comparison
