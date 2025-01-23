import streamlit as st
import sqlite3
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Initialize the database (create tables if they don't exist)
def init_db():
    conn = sqlite3.connect('issues.db')
    c = conn.cursor()

    # Create users table if it doesn't exist
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')

    # Create issues table if it doesn't exist
    c.execute('''
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student TEXT,
            issue_type TEXT,
            description TEXT,
            status TEXT DEFAULT 'Pending',
            urgency TEXT DEFAULT 'Low',
            date_posted DATE
        )
    ''')

    conn.commit()
    conn.close()

# Helper function to send email notifications
def send_email(recipient_email, subject, body):
    sender_email = "your_email@example.com"
    sender_password = "your_password"

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
        print(f"Email sent to {recipient_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")

# Authentication function for login
def login(username, password):
    conn = sqlite3.connect('issues.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = c.fetchone()
    conn.close()
    return user

# Student dashboard for posting an issue
def student_dashboard(username):
    st.title(f"Welcome, {username}")
    st.subheader("Post an Issue")

    issue_type = st.selectbox("Select Issue Type", ["Academic", "Hostel", "Mess", "Other"])
    urgency = st.selectbox("Select Urgency", ["Low", "Medium", "High"])  # Add urgency selection
    description = st.text_area("Describe the Issue")
    
    if st.button("Submit"):
        post_issue(username, issue_type, description, urgency)
        st.success("Issue Posted Successfully!")

# Post an issue into the database
def post_issue(student, issue_type, description, urgency):
    conn = sqlite3.connect('issues.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO issues (student, issue_type, description, status, urgency, date_posted) 
        VALUES (?, ?, ?, 'Pending', ?, ?)
    ''', (student, issue_type, description, urgency, datetime.now()))
    conn.commit()
    conn.close()

# Coordinator dashboard with filtering options
def coordinator_dashboard(role):
    st.title(f"{role} Dashboard")
    st.subheader("View and Manage Issues")

    # Filtering options
    filter_urgency = st.selectbox("Filter by Urgency", ["All", "Low", "Medium", "High"])
    filter_status = st.selectbox("Filter by Status", ["All", "Pending", "In Progress", "Resolved"])
    filter_date = st.date_input("Filter by Date", value=None)  # Optional date filtering

    # Fetch filtered issues based on selected role
    issues = get_filtered_issues_by_role(role, filter_urgency, filter_status, filter_date)

    if issues:
        for issue in issues:
            st.write(f"Issue #{issue[0]} by {issue[1]}")
            st.write(f"Type: {issue[2]}")
            st.write(f"Urgency: {issue[5]}")
            st.write(f"Description: {issue[3]}")
            st.write(f"Status: {issue[4]}")
            st.write(f"Date Posted: {issue[6]}")

            # Update Status
            new_status = st.selectbox("Update Status", ["Pending", "In Progress", "Resolved"], key=issue[0])
            if st.button(f"Update Issue #{issue[0]}"):
                update_issue_status(issue[0], new_status)
                st.success(f"Issue #{issue[0]} updated to {new_status}")
    else:
        st.info("No issues found.")

# Function to fetch filtered issues based on role and filters
def get_filtered_issues_by_role(role, filter_urgency, filter_status, filter_date):
    conn = sqlite3.connect('issues.db')
    c = conn.cursor()

    # Base query
    query = "SELECT * FROM issues WHERE "

    # Role-based filtering
    if role == "Academic Coordinator":
        query += "issue_type = 'Academic' "
    elif role == "Warden":
        query += "issue_type IN ('Hostel', 'Mess') "
    elif role == "Year Coordinator":
        query += "1=1 "  # For Year Coordinators, get all issues

    # Urgency filter
    if filter_urgency != "All":
        query += f"AND urgency = '{filter_urgency}' "

    # Status filter
    if filter_status != "All":
        query += f"AND status = '{filter_status}' "

    # Date filter
    if filter_date:
        query += f"AND date(date_posted) = date('{filter_date}') "

    c.execute(query)
    issues = c.fetchall()
    conn.close()
    return issues

# Update the issue status and notify student
def update_issue_status(issue_id, status):
    conn = sqlite3.connect('issues.db')
    c = conn.cursor()

    # Get the student's email and issue details before updating
    c.execute("SELECT student, description FROM issues WHERE id = ?", (issue_id,))
    issue = c.fetchone()

    c.execute("UPDATE issues SET status = ? WHERE id = ?", (status, issue_id))
    conn.commit()

    # Send notification to the student
    student_email = f"{issue[0]}@example.com"  # Assuming email is the student's username
    subject = f"Issue #{issue_id} Status Updated"
    body = f"Your issue '{issue[1]}' has been updated to '{status}'."
    send_email(student_email, subject, body)

    conn.close()

# Streamlit App
def main():
    st.sidebar.title("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    role = None

    if st.sidebar.button("Login"):
        user = login(username, password)
        if user:
            st.sidebar.success(f"Logged in as {username}")
            role = user[3]  # Get the user's role from the database

            # Based on the role, show different dashboards
            if role == "Student":
                student_dashboard(username)
            elif role in ["Academic Coordinator", "Warden", "Year Coordinator"]:
                coordinator_dashboard(role)
        else:
            st.sidebar.error("Invalid Username or Password")

if __name__ == "_main_":
    init_db()  # Initialize the database when the app starts
    main()
