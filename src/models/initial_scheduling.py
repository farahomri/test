import os
import pandas as pd
from datetime import datetime
import streamlit as st

# Initialize cumulative scheduled orders list
cumulative_scheduled_orders = set()

def find_missing_sap_numbers(plannification_df, products_classified_df):
    try:
        plannification_materials = plannification_df['Material Number']
        classified_materials = products_classified_df['SAP']
        missing_materials = plannification_materials[~plannification_materials.isin(classified_materials)]

        if missing_materials.empty:
            return None
        else:
            missing_sap_list = missing_materials.tolist()
            st.warning("Please go to the manage orders page and add these SAP numbers with their routing time:")
            for material in missing_sap_list:
                st.write(f"SAP Number: {material}")
            return missing_sap_list

    except KeyError as e:
        st.error(f"Error: Missing column - {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None

def merge_orders_with_class_code(orders_df, products_classified_path):
    products_classified_df = pd.read_csv(products_classified_path)
    orders_df = orders_df.rename(columns={"Material Number": "SAP", "Material description": "Material Description", "Order": "Order ID"})
    merged_df = pd.merge(
        orders_df,
        products_classified_df[['SAP', 'routing time', 'Class', 'Class Code']],
        on='SAP',
        how='left'
    )
    return merged_df

def calculate_working_time(technicians_path, shifts_df):
    technicians = pd.read_csv(technicians_path)
    shifts = shifts_df.copy()
    shifts['Working'] = shifts['Working'].str.strip().str.lower()
    shifts['To another'] = shifts['To another'].str.strip().str.lower()
    working_technicians = shifts[(shifts['Working'] == 'yes') & (shifts['To another'] == 'no')]
    working_technicians['Break'].fillna(0, inplace=True)
    working_technicians['Extra Time'].fillna(0, inplace=True)
    working_technicians['Working Time'] = 480 + 30 - working_technicians['Break'] + working_technicians['Extra Time']
    result = pd.merge(working_technicians, technicians[['Matricule', 'Expertise Class']], on='Matricule', how='left')
    return result

def create_initial_schedule(technicians, orders):
    orders = orders.sort_values(by='routing time', ascending=False)
    technicians = technicians.sort_values(by='Working Time', ascending=False)
    schedule = []
    current_date = datetime.now().strftime('%Y-%m-%d')

    def assign_orders(technicians, orders, exact_match=True):
        assigned_orders = []
        for index, order in orders.iterrows():
            for i, technician in technicians.iterrows():
                if technician['Working Time'] == 0:
                    continue
                if exact_match and technician['Expertise Class'] != order['Class Code']:
                    continue
                elif not exact_match and technician['Expertise Class'] < order['Class Code']:
                    continue
                difference = technician['Working Time'] - order['routing time']
                status, remaining_time, remark = ('Completed', 0, '') if difference >= 0 else ('In Progress', -difference, 'Technician working time exhausted')
                technicians.at[i, 'Working Time'] = max(difference, 0)
                schedule.append({
                    'Day/Date': current_date,
                    'SAP': order['SAP'],
                    'Order ID': order['Order ID'],
                    'Material Description': order['Material Description'],
                    'Routing Time (min)': order['routing time'],
                    'Technician Matricule': technician['Matricule'],
                    'Technician Name': technician['Technician Name'],
                    'Status': status,
                    'Remaining Time': remaining_time,
                    'Remark': remark
                })
                assigned_orders.append(index)
                cumulative_scheduled_orders.add(order['SAP'])  # Add to cumulative list
                break
        return assigned_orders

    assigned_orders = assign_orders(technicians, orders, exact_match=True)
    remaining_orders = orders.drop(index=assigned_orders)
    assigned_orders += assign_orders(technicians, remaining_orders, exact_match=False)
    remaining_orders = orders.drop(index=assigned_orders)
    technicians = technicians.sort_values(by='Working Time', ascending=False)
    for index, order in remaining_orders.iterrows():
        for i, technician in technicians.iterrows():
            if technician['Working Time'] == 0:
                continue
            difference = technician['Working Time'] - order['routing time']
            status, remaining_time, remark = ('Completed', 0, '') if difference >= 0 else ('In Progress', -difference, 'Technician working time exhausted')
            technicians.at[i, 'Working Time'] = max(difference, 0)
            schedule.append({
                'Day/Date': current_date,
                'SAP': order['SAP'],
                'Order ID': order['Order ID'],
                'Material Description': order['Material Description'],
                'Routing Time (min)': order['routing time'],
                'Technician Matricule': technician['Matricule'],
                'Technician Name': technician['Technician Name'],
                'Status': status,
                'Remaining Time': remaining_time,
                'Remark': remark
            })
            cumulative_scheduled_orders.add(order['SAP'])  # Add to cumulative list
            break

    schedule_df = pd.DataFrame(schedule)
    return schedule_df, technicians

def remove_scheduled_orders(schedule_df, unscheduled_orders):
    scheduled_orders = set(schedule_df['SAP'])
    unscheduled_orders = unscheduled_orders[~unscheduled_orders['SAP'].isin(scheduled_orders)]
    return unscheduled_orders

def reassign_blocked_order(schedule_df, unscheduled_orders_df, blocked_sap, technician_id, time_spent, block_reason):
    blocked_sap = str(blocked_sap)
    technician_id = str(technician_id)
    blocked_order_index = schedule_df[(schedule_df['SAP'].astype(str) == blocked_sap) & (schedule_df['Technician Matricule'].astype(str) == technician_id)].index

    if not blocked_order_index.empty:
        blocked_order_index = blocked_order_index[0]
        schedule_df.at[blocked_order_index, 'Status'] = 'Blocked'
        schedule_df.at[blocked_order_index, 'Remark'] = f'Blocked due to: {block_reason}. Technician spent {time_spent} minutes before blocking'
        schedule_df.at[blocked_order_index, 'Remaining Time'] = schedule_df.at[blocked_order_index, 'Routing Time (min)'] - time_spent

    new_assignment = None
    next_order = schedule_df[(schedule_df['Technician Matricule'].astype(str) == technician_id) & (schedule_df['Status'] != 'Blocked')]
    if not next_order.empty:
        next_order = next_order.iloc[0]
    else:
        if unscheduled_orders_df.empty:
            raise ValueError("No unscheduled orders available to reassign.")
        small_order = unscheduled_orders_df.iloc[0]
        unscheduled_orders_df = unscheduled_orders_df.iloc[1:]
        new_assignment = small_order
        routing_time = small_order['routing time']
        difference = routing_time - time_spent
        if difference < 0:
            status = 'In Progress'
            remaining_time = abs(difference)
        elif difference == 0:
            status = 'Completed'
            remaining_time = 0
        else:
            status = 'Completed'
            remaining_time = 0

        technician_name = schedule_df.loc[blocked_order_index, 'Technician Name']

        new_row = pd.DataFrame([{
            'Day/Date': '',
            'SAP': small_order['SAP'],
            'Order ID': small_order['Order ID'],
            'Material Description': small_order['Material Description'],
            'Routing Time (min)': routing_time,
            'Technician Matricule': technician_id,
            'Technician Name': technician_name,
            'Status': status,
            'Remaining Time': remaining_time,
            'Remark': f'Reassigned from blocked order {blocked_sap}'
        }])
        schedule_df = pd.concat([schedule_df, new_row], ignore_index=True)

    return schedule_df, unscheduled_orders_df, new_assignment
