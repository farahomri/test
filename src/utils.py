import streamlit as st
from models.technicians import load_technicians, add_technician, modify_technician, delete_technician

# Function to manage technicians
def manage_technicians():
    st.header("Manage Technicians")

    # Load technicians data
    technicians = load_technicians('data/technicians_file.csv')

    # Display technicians data
    if technicians:
        st.subheader("Current Technicians")
        technicians_data = [tech.to_dict() for tech in technicians]
        st.table(technicians_data)
    else:
        st.write("No technicians available.")

    # Add technician
    st.subheader("Add a Technician")
    matricule = st.text_input("Matricule")
    nom_prenom = st.text_input("Nom et prénom")
    niveau_4 = st.text_input("Niveau 4")
    niveau_3 = st.text_input("Niveau 3")
    niveau_2 = st.text_input("Niveau 2")
    niveau_1 = st.text_input("Niveau 1")
    classification = st.text_input("Classification")
    expertise_class = st.text_input("Expertise Class")
    if st.button("Add Technician"):
        success, message = add_technician(matricule, nom_prenom, niveau_4, niveau_3, niveau_2, niveau_1, classification, expertise_class)
        if success:
            st.success(message)
        else:
            st.error(message)

    # Modify technician
    st.subheader("Modify a Technician")
    matricule_modify = st.text_input("Matricule to modify")
    new_data = {
        'Nom et prénom': st.text_input("New Nom et prénom"),
        'Niveau 4': st.text_input("New Niveau 4"),
        'Niveau 3': st.text_input("New Niveau 3"),
        'Niveau 2': st.text_input("New Niveau 2"),
        'Niveau 1': st.text_input("New Niveau 1"),
        'Classification': st.text_input("New Classification"),
        'Expertise Class': st.text_input("New Expertise Class")
    }
    if st.button("Modify Technician"):
        success, message = modify_technician(matricule_modify, new_data)
        if success:
            st.success(message)
        else:
            st.error(message)

    # Delete technician
    st.subheader("Delete a Technician")
    matricule_delete = st.text_input("Matricule to delete")
    if st.button("Delete Technician"):
        success, message = delete_technician(matricule_delete)
        if success:
            st.success(message)
        else:
            st.error(message)

# Main function
def main():
    st.title("Technicians Management App")

    # Sidebar navigation
    page = st.sidebar.selectbox("Select a page", ["Manage Technicians"])

    if page == "Manage Technicians":
        manage_technicians()

if __name__ == "__main__":
    main()
#%%

#%%
