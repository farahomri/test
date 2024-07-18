import pandas as pd
from datetime import datetime

def filter_orders_by_status_update(schedule_df):
    in_progress_orders = schedule_df[schedule_df['Status'].str.strip().str.lower() == 'in progress']
    return in_progress_orders

def update_schedule(working_technicians_df, filter_orders_df, initial_unscheduled_orders):
    working_technicians = working_technicians_df.copy()
    filter_orders = filter_orders_df.copy()
    current_date = datetime.now().strftime('%Y-%m-%d')
    new_schedule_rows = []
    assigned_orders_ids = set()

    for index, order in filter_orders.iterrows():
        sap = order['SAP']
        order_id = order['Order ID']
        technician_matricule = order['Technician Matricule']
        remaining_time = order['Remaining Time']
        status = order['Status']
        technician_info = working_technicians[working_technicians['Matricule'] == technician_matricule]

        if not technician_info.empty:
            working_time = technician_info.iloc[0]['Working Time']
            if working_time >= remaining_time:
                new_status = 'Completed'
                new_remaining_time = 0
                new_working_time = working_time - remaining_time
            else:
                new_status = 'In Progress'
                new_remaining_time = remaining_time - working_time
                new_working_time = 0
            working_technicians.loc[working_technicians['Matricule'] == technician_matricule, 'Working Time'] = new_working_time
        else:
            new_status = status
            new_remaining_time = remaining_time
            new_working_time = 0

        new_row = {
            'Day/Date': current_date,
            'SAP': sap,
            'Order ID': order_id,
            'Material Description': order['Material Description'],
            'Routing Time (min)': order['Routing Time (min)'],
            'Technician Matricule': technician_matricule,
            'Technician Name': order['Technician Name'],
            'Status': new_status,
            'Remaining Time': new_remaining_time,
            'Remark': order.get('Remark', '')  # Default to empty if 'Remark' is missing
        }
        new_schedule_rows.append(new_row)
        assigned_orders_ids.add(order_id)

    new_schedule = pd.DataFrame(new_schedule_rows)

    # Update initial_unscheduled_orders
    initial_unscheduled_orders = initial_unscheduled_orders[~initial_unscheduled_orders['SAP'].isin(assigned_orders_ids)]

    return new_schedule, working_technicians, assigned_orders_ids, initial_unscheduled_orders

def assign_orders_with_exceptions(working_technicians_df, unscheduled_orders_df):
    working_technicians = working_technicians_df.copy()
    unscheduled_orders = unscheduled_orders_df.copy()
    unscheduled_orders = unscheduled_orders.sort_values(by='routing time', ascending=False)
    working_technicians = working_technicians.sort_values(by='Working Time', ascending=False)
    current_date = datetime.now().strftime('%Y-%m-%d')
    new_schedule_rows = []
    new_working_times = {}
    assigned_orders_ids = set()

    for tech_index, technician in working_technicians.iterrows():
        technician_matricule = technician['Matricule']
        technician_name = technician['Technician Name']
        technician_classification = technician['Expertise Class']  # Ensure the column name matches your data
        working_time = technician['Working Time']

        if working_time == 0:
            new_working_times[technician_matricule] = working_time
            continue

        while working_time > 0 and not unscheduled_orders.empty:
            suitable_orders = unscheduled_orders[unscheduled_orders['Class Code'] <= technician_classification]
            if suitable_orders.empty:
                highest_class_order = unscheduled_orders.iloc[0]
                class_mismatch = True
            else:
                highest_class_order = suitable_orders.iloc[0]
                class_mismatch = False

            order_id = highest_class_order['Order ID']
            sap = highest_class_order['SAP']
            material_description = highest_class_order['Material Description']
            routing_time = highest_class_order['routing time']
            class_code = highest_class_order['Class Code']
            difference = working_time - routing_time

            if difference < 0:
                status = 'In Progress'
                remaining_time = routing_time - working_time
                remark = 'Technician working time exhausted' if class_mismatch else ''
                working_time = 0
            elif difference == 0:
                status = 'Completed'
                remaining_time = 0
                remark = 'Technician working time exhausted' if class_mismatch else ''
                working_time = 0
            else:
                status = 'Completed'
                remaining_time = 0
                remark = 'Technician working time exhausted' if class_mismatch else ''
                working_time = difference

            new_row = {
                'Day/Date': current_date,
                'SAP': sap,
                'Order ID': order_id,
                'Material Description': material_description,
                'Routing Time (min)': routing_time,
                'Technician Matricule': technician_matricule,
                'Technician Name': technician_name,
                'Status': status,
                'Remaining Time': remaining_time,
                'Remark': remark
            }
            new_schedule_rows.append(new_row)
            unscheduled_orders = unscheduled_orders[unscheduled_orders['Order ID'] != order_id]
            assigned_orders_ids.add(order_id)

        new_working_times[technician_matricule] = working_time

    new_schedule = pd.DataFrame(new_schedule_rows)
    return new_schedule, unscheduled_orders, assigned_orders_ids

def final_update(new_schedule_df, schedule_with_exceptions_df):
    final_df = pd.concat([new_schedule_df, schedule_with_exceptions_df], ignore_index=True)
    return final_df

def reassign_blocked_order_update(schedule_df, unscheduled_orders_df, blocked_sap, technician_id, time_spent):
    blocked_sap = str(blocked_sap)
    technician_id = str(technician_id)
    blocked_order_index = schedule_df[(schedule_df['SAP'] == blocked_sap) & (schedule_df['Order ID'] == blocked_sap) & (schedule_df['Technician Matricule'] == technician_id)].index

    if not blocked_order_index.empty:
        blocked_order_index = blocked_order_index[0]
        schedule_df.at[blocked_order_index, 'Status'] = 'Blocked'
        schedule_df.at[blocked_order_index, 'Remark'] = f'Technician spent {time_spent} minutes before blocking'
        schedule_df.at[blocked_order_index, 'Remaining Time'] = schedule_df.at[blocked_order_index, 'Routing Time (min)'] - time_spent

    new_assignment = None
    next_order = schedule_df[(schedule_df['Technician Matricule'] == technician_id) & (schedule_df['Status'] != 'Blocked')]
    if not next_order.empty:
        next_order = next_order.iloc[0]
    else:
        if unscheduled_orders_df.empty:
            return schedule_df, unscheduled_orders_df, None
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

def get_unscheduled_orders(old_unscheduled_orders, final_updated_schedule):
    updated_unscheduled_orders = old_unscheduled_orders[~old_unscheduled_orders['SAP'].isin(final_updated_schedule['SAP'])]
    return updated_unscheduled_orders
