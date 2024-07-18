import pandas as pd
import streamlit as st
#from src.models.update_scheduling import update_schedule

# Function to get the schedule from session state
def get_schedule():
    if 'updated_schedule_df' in st.session_state and st.session_state['updated_schedule_df'] is not None:
        return st.session_state['updated_schedule_df']
    elif 'schedule_df' in st.session_state and st.session_state['schedule_df'] is not None:
        return st.session_state['schedule_df']
    else:
        st.error("No schedule data found in session state.")
        return None

def get_assigned_technician(order_id):
    schedule = get_schedule()
    if schedule is not None:
        technician = schedule.loc[schedule['Order ID'] == order_id, 'Technician Name']
        if not technician.empty:
            return technician.values[0]
        else:
            return "No technician assigned for this order ID."
    else:
        return "No schedule data available."

def get_order_status(order_id):
    schedule = get_schedule()
    if schedule is not None:
        status = schedule.loc[schedule['Order ID'] == order_id, 'Status']
        if not status.empty:
            return status.values[0]
        else:
            return "No status found for this order ID."
    else:
        return "No schedule data available."

def list_orders_by_technician(technician_id):
    schedule = get_schedule()
    if schedule is not None:
        orders = schedule.loc[schedule['Technician Matricule'] == technician_id, 'SAP Order ID'].tolist()
        if orders:
            return orders
        else:
            return "No orders found for this technician ID."
    else:
        return "No schedule data available."

def count_in_progress_orders():
    schedule = get_schedule()
    if schedule is not None:
        count = schedule[schedule['Status'] == 'In Progress'].shape[0]
        return count
    else:
        return "No schedule data available."

def get_order_classification(order_id):
    products_file = '../data/products_classified.csv'
    products = pd.read_csv(products_file)
    classification = products.loc[products['Order ID'] == order_id, 'Class Code']
    if not classification.empty:
        return classification.values[0]
    else:
        return "No classification found for this order ID."

'''def get_available_technicians(working_technicians_file, filter_orders_file, output_file):
    updated_technicians = update_schedule(working_technicians_file, filter_orders_file, output_file)
    available_technicians = updated_technicians[updated_technicians['Working Time'] > 0]
    return available_technicians['Technician Name'].tolist()'''

def get_technician_classification(technician_id):
    technicians_file = '../data/technicians_file.csv'
    technicians = pd.read_csv(technicians_file)
    classification = technicians.loc[technicians['Matricule'] == technician_id, 'Classification']
    if not classification.empty:
        return classification.values[0]
    else:
        return "No classification found for this technician ID."

def count_completed_orders():
    schedule = get_schedule()
    if schedule is not None:
        count = schedule[schedule['Status'] == 'Completed'].shape[0]
        return count
    else:
        return "No schedule data available."

intents = {
    "assigned_technician": get_assigned_technician,
    "order_status": get_order_status,
    "list_orders_by_technician": list_orders_by_technician,
    "count_in_progress_orders": count_in_progress_orders,
    "order_classification": get_order_classification,
    #"available_technicians": get_available_technicians,
    "technician_classification": get_technician_classification,
    "completed_orders": count_completed_orders,
}

#%%
