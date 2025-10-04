# Expense Tracker Django Project

![GitHub last commit](https://img.shields.io/github/last-commit/Hamzah1507/expense-tracker-odoo-x-amalthea)
![GitHub repo size](https://img.shields.io/github/repo-size/Hamzah1507/expense-tracker-odoo-x-amalthea)
![Python](https://img.shields.io/badge/python-3.12.3-blue)
![Django](https://img.shields.io/badge/django-5.2.5-green)

A modern **Django-based Expense Tracker** for individuals and teams to efficiently manage, submit, and approve expenses.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Screenshots](#screenshots)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- User authentication and role management (Admin, Employee)
- Submit expenses with:
  - Categories
  - Descriptions
  - Amounts
  - Receipts (image upload)
  - Currency selection with conversion
- Expense approval workflow:
  - Draft → Pending → Approved/Rejected
- View expense history with filters:
  - Status (Draft, Pending, Approved, Rejected)
  - Date range
- Receipt image preview before submission
- Pagination for long lists
- REST API endpoints for integration with other apps
- Responsive, modern frontend using Bootstrap 5

---

## Tech Stack

- **Backend:** Django 5.2.5, Django REST Framework  
- **Frontend:** Bootstrap 5, HTML, CSS, JavaScript, FontAwesome  
- **Database:** SQLite (default, can switch to PostgreSQL/MySQL)  
- **Authentication:** Django Authentication + JWT (for APIs)  
- **Version Control:** Git & GitHub

---

## Installation

1. **Clone the repository**

```bash
git clone https://github.com/Hamzah1507/expense-tracker-odoo-x-amalthea.git
cd expense-tracker-odoo-x-amalthea
