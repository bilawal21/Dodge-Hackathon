import sqlite3
from faker import Faker

# Function to format phone numbers in (XXX) XXX-XXXX format
def generate_us_phone_number():
    return f"{fake.numerify('###')}-{fake.numerify('###')}-{fake.numerify('####')}"

# Create the database and table
def create_database():
    conn = sqlite3.connect("form_data.db")
    cursor = conn.cursor()

    # Create table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            unique_id TEXT PRIMARY KEY,
            full_name TEXT,
            phone_number TEXT,
            street_address TEXT,
            city TEXT,
            state TEXT,
            postal_code TEXT,
            country TEXT
        )
    ''')
    
    # Initialize Faker with USA locale
    global fake
    fake = Faker("en_US")

    # Generate sample data
    sample_data = [
        (
            f"UID{i:03d}",
            fake.name(),
            generate_us_phone_number(),  # Enforce USA phone format
            fake.street_address(),
            fake.city(),
            fake.state_abbr(),  # Use state abbreviation
            fake.zipcode(),
            "United States"
        )
        for i in range(1, 6)  # Generate 5 sample records
    ]

    # Insert data into the table
    cursor.executemany('''
        INSERT OR IGNORE INTO users (
            unique_id, full_name, phone_number, street_address,
            city, state, postal_code, country
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', sample_data)

    conn.commit()
    conn.close()
    print("Database created and sample data added!")

# Run the function to create database
if __name__ == "__main__":
    create_database()
