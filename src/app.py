import os
import sys
from collections import Counter
import streamlit as st
import pandas as pd
from models.orders import load_orders, add_order, modify_order, delete_order
from chatbot.chatbot_functions import handle_user_input
from models.initial_scheduling import find_missing_sap_numbers, merge_orders_with_class_code, calculate_working_time, create_initial_schedule, remove_scheduled_orders, reassign_blocked_order
from models.technicians import load_technicians, save_technicians, add_technician, modify_technician, delete_technician
from models.reclamations import load_reclamations, add_reclamation, modify_reclamation, delete_reclamation
from models.update_scheduling import filter_orders_by_status_update,get_unscheduled_orders, update_schedule, assign_orders_with_exceptions, final_update, reassign_blocked_order_update

VALID_CREDENTIALS = {
    "admin": "password123",
    "user": "userpassword"
}
def login():
    """Handles user authentication."""
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        st.header("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if username in VALID_CREDENTIALS and VALID_CREDENTIALS[username] == password:
                st.session_state['logged_in'] = True
                st.success("Logged in successfully!")
                st.experimental_rerun()  # Refresh the page after successful login
            else:
                st.error("Invalid username or password. Please try again.")
        return False  # Return False to indicate not logged in
    return True  # Return True to indicate successful login

def logout():
    """Logs out the user and clears the session."""
    st.session_state['logged_in'] = False
    st.experimental_rerun()



def initialize_session_state():
    if 'initial_schedule_df' not in st.session_state:
        st.session_state['initial_schedule_df'] = None
    if 'updated_schedule_df' not in st.session_state:
        st.session_state['updated_schedule_df'] = None
def create_empty_technicians_file(file_path):
    if not os.path.exists(file_path):
        df = pd.DataFrame(columns=['Matricule', 'Nom et prénom', 'Niveau 4', 'Niveau 3', 'Niveau 2', 'Niveau 1', 'Classification', 'Expertise Class'])
        df.to_csv(file_path, index=False)

# Function to create an empty reclamations file with headers if it doesn't exist
def create_empty_reclamations_file(file_path):
    if not os.path.exists(file_path):
        df = pd.DataFrame(columns=['Date', 'Ordre', 'SAP', 'Description', 'Qty', 'Reclamation', 'Remarque', 'Technicien', 'Decision', 'QS'])
        df.to_excel(file_path, index=False)

# Function to manage technicians
def display_statistics(technicians):
    st.subheader("Technicians Statistics")

    # Create a DataFrame for easier manipulation
    df = pd.DataFrame([tech.to_dict() for tech in technicians])

    # Display counts of each classification
    st.write("### Classification Counts")
    classification_counts = df['Classification'].value_counts()
    st.bar_chart(classification_counts)



    # Display basic statistics
    st.write("### Basic Statistics")
    st.write(df.describe())

def manage_technicians():
    st.header("Manage Technicians")

    technicians_file_path = '../data/technicians_file.csv'  # Adjusted path to go up one level from 'src'

    create_empty_technicians_file(technicians_file_path)

    try:
        technicians = load_technicians(technicians_file_path)
    except FileNotFoundError:
        st.error(f"File not found: {technicians_file_path}")
        return

    # Initialize the toggle state in session state if not present
    if 'show_technicians' not in st.session_state:
        st.session_state['show_technicians'] = False

    # Toggle button
    if st.checkbox("Show/Hide Technicians"):
        st.session_state['show_technicians'] = not st.session_state['show_technicians']

    # Show technicians if the toggle state is True
    if st.session_state['show_technicians']:
        st.subheader("Current Technicians")
        technicians_data = [tech.to_dict() for tech in technicians]
        st.table(pd.DataFrame(technicians_data))

        display_statistics(technicians)

    with st.expander("Add a Technician"):
        col1, col2 = st.columns(2)
        with col1:
            matricule = st.text_input("Matricule")
            nom_prenom = st.text_input("Nom et prénom")
            niveau_4 = st.text_input("Niveau 4")
            niveau_3 = st.text_input("Niveau 3")
        with col2:
            niveau_2 = st.text_input("Niveau 2")
            niveau_1 = st.text_input("Niveau 1")
        if st.button("Add Technician"):
            success, message = add_technician(matricule, nom_prenom, niveau_4, niveau_3, niveau_2, niveau_1, technicians_file_path)
            if success:
                st.success(message)
                st.experimental_rerun()  # Refresh the page to display the updated table
            else:
                st.error(message)

    with st.expander("Modify a Technician"):
        matricule_modify = st.text_input("Matricule to modify")
        new_data = {
            'Nom et prénom': st.text_input("New Nom et prénom"),
            'Niveau 4': st.text_input("New Niveau 4"),
            'Niveau 3': st.text_input("New Niveau 3"),
            'Niveau 2': st.text_input("New Niveau 2"),
            'Niveau 1': st.text_input("New Niveau 1")
        }
        if st.button("Modify Technician"):
            success, message = modify_technician(matricule_modify, new_data, technicians_file_path)
            if success:
                st.success(message)
                st.experimental_rerun()  # Refresh the page to display the updated table
            else:
                st.error(message)

    with st.expander("Delete a Technician"):
        matricule_delete = st.text_input("Matricule to delete")
        if st.button("Delete Technician"):
            success, message = delete_technician(matricule_delete, technicians_file_path)
            if success:
                st.success(message)
                st.experimental_rerun()  # Refresh the page to display the updated table
            else:
                st.error(message)
    st.header("Technicians Statistics")

    # Create a DataFrame for easier manipulation
    df = pd.DataFrame([tech.to_dict() for tech in technicians])

    # Display counts of each classification
    st.write("### Classification Counts")
    classification_counts = df['Classification'].value_counts()
    st.bar_chart(classification_counts)



    # Display basic statistics
    st.write("### Basic Statistics")
    st.write(df.describe())

# Function to manage reclamations
def generate_recommendations(reclamations):
    recommendations = []
    seen_technicians = set()
    for rec in reclamations:
        if rec.decision in ["entretien individuel", "Entretien Oral"]:
            if rec.technicien not in seen_technicians:
                recommendations.append({
                    'Technicien': rec.technicien,
                    'Decision': rec.decision,
                    'Recommendation': "Suggest training or decrease in expertise level"
                })
                seen_technicians.add(rec.technicien)
    return recommendations

def manage_reclamations():
    st.header("Manage Reclamations")

    reclamations_file_path = '../data/reclamations_file.xlsx'  # Adjusted path to go up one level from 'src'

    # Create the file if it doesn't exist
    create_empty_reclamations_file(reclamations_file_path)

    # Load reclamations data
    reclamations = load_reclamations(reclamations_file_path)

    # Initialize the toggle state in session state if not present
    if 'show_reclamations' not in st.session_state:
        st.session_state['show_reclamations'] = False

    # Toggle button
    if st.checkbox("Show/Hide Reclamations"):
        st.session_state['show_reclamations'] = not st.session_state['show_reclamations']

    # Show reclamations if the toggle state is True
    if st.session_state['show_reclamations']:
        if reclamations:
            st.subheader("Current Reclamations")
            reclamations_data = [rec.to_dict() for rec in reclamations]
            st.table(pd.DataFrame(reclamations_data))
        else:
            st.write("No reclamations available.")

    with st.expander("Add a Reclamation"):
        col1, col2 = st.columns(2)
        with col1:
            date = st.text_input("Date")
            ordre = st.text_input("Ordre")
            sap = st.text_input("SAP")
            description = st.text_input("Description")
        with col2:
            qty = st.text_input("Qty")
            reclamation = st.text_input("Reclamation")
            remarque = st.text_input("Remarque")
            technicien = st.text_input("Technicien")
            decision = st.text_input("Decision")
            qs = st.text_input("QS")
        if st.button("Add Reclamation"):
            success, message = add_reclamation(date, ordre, sap, description, qty, reclamation, remarque, technicien, decision, qs, reclamations_file_path)
            if success:
                st.success(message)
                st.experimental_rerun()  # Refresh the page to display the updated table
            else:
                st.error(message)

    with st.expander("Modify a Reclamation"):
        ordre_modify = st.text_input("Ordre to modify")
        new_data = {
            'Date': st.text_input("New Date"),
            'SAP': st.text_input("New SAP"),
            'Description': st.text_input("New Description"),
            'Qty': st.text_input("New Qty"),
            'Reclamation': st.text_input("New Reclamation"),
            'Remarque': st.text_input("New Remarque"),
            'Technicien': st.text_input("New Technicien"),
            'Decision': st.text_input("New Decision"),
            'QS': st.text_input("New QS")
        }
        if st.button("Modify Reclamation"):
            success, message = modify_reclamation(ordre_modify, new_data, reclamations_file_path)
            if success:
                st.success(message)
                st.experimental_rerun()  # Refresh the page to display the updated table
            else:
                st.error(message)

    with st.expander("Delete a Reclamation"):
        ordre_delete = st.text_input("Ordre to delete")
        if st.button("Delete Reclamation"):
            success, message = delete_reclamation(ordre_delete, reclamations_file_path)
            if success:
                st.success(message)
                st.experimental_rerun()  # Refresh the page to display the updated table
            else:
                st.error(message)

    # Generate and display recommendations
    st.subheader("Recommendations")
    recommendations = generate_recommendations(reclamations)
    if recommendations:
        st.table(pd.DataFrame(recommendations))
    else:
        st.write("No recommendations available.")
def initial_scheduling_and_manage_blocked_orders():
    st.header("Initial Scheduling and Manage Blocked Orders")

    st.subheader("Initial Scheduling")

    # Ensure the schedule is persistent between page navigation
    if 'initial_schedule_df' not in st.session_state:
        st.session_state['initial_schedule_df'] = None
    if 'unscheduled_orders_df' not in st.session_state:
        st.session_state['unscheduled_orders_df'] = None
    if 'merged_orders' not in st.session_state:
        st.session_state['merged_orders'] = None

    # Only allow new file upload if no previous schedule exists, or if users want to replace it
    uploaded_orders = st.file_uploader("Upload Orders File", type=['xlsx'], key="initial_orders")
    uploaded_shifts = st.file_uploader("Upload Shifts File", type=['xlsx'], key="initial_shifts")

    if uploaded_orders and uploaded_shifts:
        # Load the new orders and shifts data
        orders_df = pd.read_excel(uploaded_orders)
        shifts_df = pd.read_excel(uploaded_shifts)

        # Process the data as before
        products_classified_path = '../data/products_classified.csv'
        technicians_file_path = '../data/technicians_file.csv'
        products_classified_df = pd.read_csv(products_classified_path)

        missing_sap_numbers = find_missing_sap_numbers(orders_df, products_classified_df)
        if missing_sap_numbers:
            st.stop()

        merged_orders = merge_orders_with_class_code(orders_df, products_classified_path)
        working_technicians = calculate_working_time(technicians_file_path, shifts_df)

        schedule_df, technicians_with_classification = create_initial_schedule(working_technicians, merged_orders)

        # Store the schedule and related data in session state
        st.session_state['initial_schedule_df'] = schedule_df
        st.session_state['unscheduled_orders_df'] = remove_scheduled_orders(schedule_df, merged_orders)
        st.session_state['merged_orders'] = merged_orders

        st.write("Initial Schedule")
        st.dataframe(schedule_df)

    # If schedule already exists in session state, show it
    elif st.session_state['initial_schedule_df'] is not None:
        st.write("Initial Schedule (from session)")
        st.dataframe(st.session_state['initial_schedule_df'])

    st.subheader("Reassign Blocked Orders")

    sap_number = st.text_input("SAP Order Number")
    technician_matricule = st.text_input("Technician Matricule")
    time_spent = st.number_input("Time Spent (minutes)", min_value=0)
    block_reason = st.selectbox(
        "Select Block Reason",
        [
            "Probleme Gravure SAP", "Ordre soudure NOK", "Qualite Soudure NOK", "Wackler",
            "Probleme DP", "Serrage", "Manque Piece", "Probleme Test IR : SV, accessoires ....",
            "Probleme SV", "Probleme Activation", "Manque etiquette", "court circuit",
            "Montabilité", "Aspect Visuelle"
        ]
    )

    if st.button("Reassign Blocked Order"):
        if 'schedule_df' in st.session_state and 'unscheduled_orders_df' in st.session_state:
            updated_schedule_df, updated_unscheduled_orders_df, new_order = reassign_blocked_order(
                st.session_state['schedule_df'], st.session_state['unscheduled_orders_df'],
                sap_number, technician_matricule, time_spent, block_reason
            )

            if new_order is not None:
                st.write("New Assigned Order")
                st.dataframe(new_order)

            st.session_state['schedule_df'] = updated_schedule_df
            st.session_state['unscheduled_orders_df'] = updated_unscheduled_orders_df
            st.write("Updated Schedule")
            st.dataframe(updated_schedule_df)

            # Append the blocked order details to the file
            blocked_order_details = {
                "SAP Order Number": sap_number,
                "Technician Matricule": technician_matricule,
                "Time Spent": time_spent,
                "Block Reason": block_reason
            }
            blocked_orders_df = pd.DataFrame([blocked_order_details])
            blocked_orders_df.to_csv(blocked_orders_file_path, mode='a', index=False, header=False)

    # Display statistics about blocked orders
    st.subheader("Blocked Orders Statistics")

    if st.button("Show Statistics"):
        if os.path.exists(blocked_orders_file_path):
            blocked_orders_stats_df = pd.read_csv(blocked_orders_file_path)
            block_reason_counts = Counter(blocked_orders_stats_df['Block Reason'])
            technician_block_counts = Counter(blocked_orders_stats_df['Technician Matricule'])

            st.write("Number of Blocked Orders per Category")
            st.dataframe(pd.DataFrame(block_reason_counts.items(), columns=['Block Reason', 'Count']))

            st.write("Technician with Most Blocked Orders")
            st.dataframe(pd.DataFrame(technician_block_counts.items(), columns=['Technician Matricule', 'Count']))
        else:
            st.write("No blocked orders data available.")

# Function for update scheduling
def update_scheduling():
    st.header("Update Scheduling")


    # Ensure the schedule from the initial scheduling is available
    if 'initial_schedule_df' not in st.session_state or st.session_state['initial_schedule_df'] is None:
        st.error("Please complete the initial scheduling first before updating the schedule.")
        return

    # Ensure the updated schedule is persistent between page navigation
    if 'updated_schedule_df' not in st.session_state:
        st.session_state['updated_schedule_df'] = None

    # Shifts file uploader, to trigger an update when new shifts are uploaded
    uploaded_shifts = st.file_uploader("Upload Shifts File", type=['xlsx'], key="update_shifts")

    # If new shifts file is uploaded, recalculate the schedule
    if uploaded_shifts:
        shifts_df = pd.read_excel(uploaded_shifts)

        # Use the schedule stored in session state from the initial scheduling page
        schedule_df = st.session_state['initial_schedule_df']
        orders_df = st.session_state.get('merged_orders')
        technicians_file_path = '../data/technicians_file.csv'

        # Calculate working time
        working_technicians = calculate_working_time(technicians_file_path, shifts_df)

        # Filter orders by status
        in_progress_orders = filter_orders_by_status_update(schedule_df)

        # Maintain initial unscheduled orders
        if 'unscheduled_orders_df' not in st.session_state:
            st.session_state['unscheduled_orders_df'] = orders_df.copy()

        # Update schedule
        new_schedule, updated_working_technicians, assigned_orders_ids, updated_unscheduled_orders_df = update_schedule(
            working_technicians, in_progress_orders, st.session_state['unscheduled_orders_df']
        )

        # Assign orders with exceptions
        schedule_with_exceptions, unscheduled_orders, assigned_orders_ids = assign_orders_with_exceptions(
            updated_working_technicians, updated_unscheduled_orders_df
        )

        # Final update
        final_schedule = final_update(new_schedule, schedule_with_exceptions)

        # Store the updated schedule in session state
        st.session_state['updated_schedule_df'] = final_schedule
        st.session_state['unscheduled_orders_df'] = unscheduled_orders

        # Display the updated schedule
        st.write("Final Updated Schedule")
        st.dataframe(final_schedule)

    # If no new shifts file is uploaded, display the existing updated schedule from session state
    elif st.session_state['updated_schedule_df'] is not None:
        st.write("Final Updated Schedule (from session)")
        st.dataframe(st.session_state['updated_schedule_df'])

    else:
        st.info("Please upload the shifts file to proceed with schedule updates.")
    st.subheader("Reassign Blocked Orders")

    sap_number = st.text_input("SAP Order Number")
    technician_matricule = st.text_input("Technician Matricule")
    time_spent = st.number_input("Time Spent (minutes)", min_value=0)
    block_reason = st.selectbox(
        "Select Block Reason",
        [
            "Probleme Gravure SAP", "Ordre soudure NOK", "Qualite Soudure NOK", "Wackler",
            "Probleme DP", "Serrage", "Manque Piece", "Probleme Test IR : SV, accessoires ....",
            "Probleme SV", "Probleme Activation", "Manque etiquette", "court circuit",
            "Montabilité", "Aspect Visuelle"
        ]
    )

    if st.button("Reassign Blocked Order"):
        if 'schedule_df' in st.session_state and 'unscheduled_orders_df' in st.session_state:
            updated_schedule_df, updated_unscheduled_orders_df, new_order = reassign_blocked_order_update(
                st.session_state['schedule_df'], st.session_state['unscheduled_orders_df'],
                sap_number, technician_matricule, time_spent
            )

            if new_order is not None:
                st.write("New Assigned Order")
                st.dataframe(new_order)

            st.session_state['schedule_df'] = updated_schedule_df
            st.session_state['unscheduled_orders_df'] = updated_unscheduled_orders_df
# Define a list of predefined questions for the chatbot
questions = {
    "Get Assigned Technician for an Order": "assigned_technician",
    "Get Status of an Order": "order_status",
    "List Orders by Technician": "list_orders_by_technician",
    "Count In Progress Orders": "count_in_progress_orders",
    "Get Classification of an Order": "order_classification",
    "Get Technician Classification": "technician_classification",
    "Count Completed Orders": "count_completed_orders",
}

# Function to handle chatbot interaction

def chatbot():
    st.header("Chatbot")
    user_input = st.text_area("Ask me anything (e.g., 'Who is assigned to order 123456?')")

    if st.button("Ask"):
        if user_input.strip():
            response = handle_user_input(user_input)
            st.write(f"Bot: {response}")
        else:
            st.write("Please enter a question.")
# Define the path to the products_classified file
products_classified_path = '../data/products_classified.csv'

# Define a function to create an empty file if it doesn't exist
def create_empty_file(file_path, columns):
    if not os.path.exists(file_path):
        df = pd.DataFrame(columns=columns)
        df.to_csv(file_path, index=False)

# Create the products_classified file if it doesn't exist
create_empty_file(products_classified_path, ['SAP', 'Material Description', 'routing time', 'Class', 'Class Code'])


def manage_orders():
    st.header("Manage Orders")

    # Load products_classified data
    try:
        df_orders = load_orders(products_classified_path)
        print("Loaded Products Classified DataFrame columns:", df_orders.columns)
    except FileNotFoundError:
        st.error(f"File not found: {products_classified_path}")
        return

    # Initialize the toggle state in session state if not present
    if 'show_orders' not in st.session_state:
        st.session_state['show_orders'] = False

    # Toggle button
    if st.checkbox("Show/Hide Orders"):
        st.session_state['show_orders'] = not st.session_state['show_orders']

    # Show orders if the toggle state is True
    if st.session_state['show_orders']:
        if not df_orders.empty:
            st.subheader("Current Orders")
            st.table(df_orders)
        else:
            st.write("No orders available.")

    with st.expander("Add an Order"):
        col1, col2 = st.columns(2)
        with col1:
            sap = st.text_input("SAP")
            material_description = st.text_input("Material Description")
            routing_time = st.number_input("Routing Time", min_value=0)
        if st.button("Add Order"):
            df_orders = add_order(df_orders, sap, material_description, routing_time, products_classified_path)
            st.success(f"Order with SAP {sap} added successfully.")
            st.experimental_rerun()  # Refresh the page to display the updated table

    with st.expander("Modify an Order"):
        sap_modify = st.text_input("SAP to modify")
        new_material_description = st.text_input("New Material Description")
        new_routing_time = st.number_input("New Routing Time", min_value=0)
        if st.button("Modify Order"):
            try:
                df_orders = modify_order(df_orders, sap_modify, new_material_description, new_routing_time, products_classified_path)
                st.success(f"Order with SAP {sap_modify} modified successfully.")
            except ValueError as e:
                st.error(str(e))
            st.experimental_rerun()  # Refresh the page to display the updated table

    with st.expander("Delete an Order"):
        sap_delete = st.text_input("SAP to delete")
        if st.button("Delete Order"):
            df_orders = delete_order(df_orders, sap_delete, products_classified_path)
            st.success(f"Order with SAP {sap_delete} deleted successfully.")
            st.experimental_rerun()  # Refresh the page to display the updated table

def main():
    # Authentication page
    if not login():  # If not logged in, stop the execution
        return  # Do not show any other content until logged in

    # Show the main application after login
    st.sidebar.title("Navigation")
    st.sidebar.button("Logout", on_click=logout)
    pages = {
        "Manage Technicians": manage_technicians,
        "Manage Reclamations": manage_reclamations,
        "Manage Orders": manage_orders,
        "Initial Scheduling ": initial_scheduling_and_manage_blocked_orders,
        "Update Scheduling": update_scheduling,
        "Chatbot": chatbot
    }

    choice = st.sidebar.radio("Go to", list(pages.keys()))
    initialize_session_state()
    pages[choice]()

if __name__ == "__main__":
    main()

#%%

#%%