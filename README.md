# Halleluyah Optical Laboratory POS

Online POS for optical lab/retail/wholesale use.

## Features
- Manager and staff login
- Manager-only product, stock, lens power, staff, and branch management
- Multi-branch inventory
- Lens inventory with SPH, CYL, AXIS, ADD and quantity per power
- Product categories: lenses, frames, cases, lens cloth, liquid lens cleaner, accessories
- Frame types: metal, plastic, rimless, designer frame
- Retail/end-user and wholesale prices in Naira
- POS sales with discount, amount paid, balance and payment method
- Debtors report and sales history
- Printable receipt/invoice
- Render deployment using PostgreSQL

## Default Login
Username: `manager`
Password: `manager123`

Change the password after deployment by creating a new manager account and removing/ignoring the default.

## Run locally
```bash
pip install -r requirements.txt
python app.py
```
Open: http://127.0.0.1:5000

## Deploy on Render with GitHub
1. Extract this ZIP.
2. Create a new GitHub repository.
3. Upload all files in this folder to the repository.
4. Go to Render.com.
5. Click **New +** > **Blueprint**.
6. Select your GitHub repository.
7. Render will read `render.yaml`, create the web service and PostgreSQL database.
8. After deployment, open the Render web URL and log in.

## Important
This is a strong working starter version. For heavy daily use, add: edit/delete records, audit logs, CSV import for bulk lens powers, payment update for debtors, and stricter password change flow.
