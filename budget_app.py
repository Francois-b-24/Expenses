import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# Connexion à la base de données SQLite
conn = sqlite3.connect('/Users/f.b/Desktop/Data_Science/Budget/Expenses/budget_app.db')
cursor = conn.cursor()

# Créer les tables si elles n'existent pas encore
cursor.execute('''
    CREATE TABLE IF NOT EXISTS revenus (
        mois TEXT PRIMARY KEY,
        revenu REAL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY,
        mois TEXT,
        poste_depense TEXT,
        budget REAL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY,
        date TEXT,
        poste_depense TEXT,
        description TEXT,
        montant REAL,
        mois TEXT
    )
''')

conn.commit()

# Titre de l'application
st.title("Suivi quotidien de budget")

# Initialisation des postes de dépenses prédéfinis
postes_depenses = ["Epargne", "Logement", "Alimentation (Cantine + Courses)", 
                   "Transport (SNCF + RATP)", "Electricité", "Internet + Mobile",
                   "Netflix", "Apple Storage", "Crédit Conso", "Basic Fit", 
                   "Loisirs", "W", "Autres"]

# Sélecteur de mois
mois_selectionne = st.selectbox(
    "Sélectionnez le mois pour le suivi",
    options=pd.date_range(start="2023-01-01", end=datetime.today(), freq='M').strftime('%Y-%m')
)

# Charger les revenus pour un mois spécifique
def charger_revenu(mois):
    cursor.execute("SELECT revenu FROM revenus WHERE mois=?", (mois,))
    result = cursor.fetchone()
    return result[0] if result else 0.0

# Sauvegarder le revenu dans la base de données
def sauvegarder_revenu(mois, revenu):
    cursor.execute('''
        INSERT OR REPLACE INTO revenus (mois, revenu) 
        VALUES (?, ?)
    ''', (mois, revenu))
    conn.commit()

# Charger les budgets pour un mois spécifique
def charger_budgets(mois):
    cursor.execute("SELECT poste_depense, budget FROM budgets WHERE mois=?", (mois,))
    lignes = cursor.fetchall()
    budgets = {poste: 0.0 for poste in postes_depenses}
    for poste_depense, budget in lignes:
        budgets[poste_depense] = budget
    return budgets

# Sauvegarder les budgets dans la base de données
def sauvegarder_budget(mois, budgets):
    for poste, montant in budgets.items():
        cursor.execute('''
            INSERT OR REPLACE INTO budgets (mois, poste_depense, budget) 
            VALUES (?, ?, ?)
        ''', (mois, poste, montant))
    conn.commit()

# Charger les transactions pour un mois spécifique
def charger_transactions(mois):
    cursor.execute("SELECT id, date, poste_depense, description, montant FROM transactions WHERE mois=?", (mois,))
    lignes = cursor.fetchall()
    transactions = pd.DataFrame(lignes, columns=["ID", "Date", "Poste de dépense", "Description", "Montant"])
    return transactions

# Sauvegarder une transaction dans la base de données
def ajouter_transaction(date, poste_depense, description, montant, mois):
    cursor.execute('''
        INSERT INTO transactions (date, poste_depense, description, montant, mois)
        VALUES (?, ?, ?, ?, ?)
    ''', (date, poste_depense, description, montant, mois))
    conn.commit()

# Interface pour définir le revenu et les budgets
st.subheader(f"Revenu pour le mois de {mois_selectionne}")
revenu = st.number_input("Revenu mensuel (€)", min_value=0.0, value=charger_revenu(mois_selectionne), step=100.0)

if st.button("Sauvegarder le revenu"):
    sauvegarder_revenu(mois_selectionne, revenu)
    st.success("Le revenu a été enregistré avec succès !")

# Interface pour définir le budget pour chaque poste de dépense
st.subheader(f"Définir le budget pour le mois de {mois_selectionne}")
budgets = charger_budgets(mois_selectionne)
for poste in postes_depenses:
    budgets[poste] = st.number_input(f"Budget pour {poste} (€)", min_value=0.0, value=budgets[poste], step=10.0)

if st.button("Sauvegarder le budget"):
    sauvegarder_budget(mois_selectionne, budgets)
    st.success("Le budget a été enregistré avec succès !")

# Formulaire pour ajouter une nouvelle dépense
st.subheader("Ajouter une nouvelle dépense")
with st.form("ajout_transaction"):
    date = st.date_input("Date", datetime.today())
    poste_depense = st.selectbox("Poste de dépense", postes_depenses)
    description = st.text_input("Description")
    montant = st.number_input("Montant de la dépense (€)", min_value=0.01, format="%.2f")
    submit = st.form_submit_button("Ajouter la dépense")
    
    if submit:
        if montant and description:
            ajouter_transaction(date, poste_depense, description, montant, mois_selectionne)
            st.success(f"Dépense de {montant} € pour {poste_depense} ajoutée !")

# Afficher les transactions du mois sélectionné
st.subheader(f"Transactions du mois de {mois_selectionne}")
transactions = charger_transactions(mois_selectionne)
if not transactions.empty:
    st.dataframe(transactions)

    # Option pour supprimer une transaction
    transaction_id = st.number_input("ID de la transaction à supprimer", min_value=1, step=1)
    if st.button("Supprimer la transaction"):
        supprimer_transaction(transaction_id)
        st.success(f"La transaction avec l'ID {transaction_id} a été supprimée.")

    # Calcul du total des dépenses par poste
    depenses_par_poste = transactions.groupby("Poste de dépense")["Montant"].sum()

    # Calcul du total des dépenses du mois
    total_depenses = transactions["Montant"].sum()

    # Affichage des budgets, dépenses et budget restant par poste
    st.subheader("État du budget par poste")
    for poste in postes_depenses:
        depense = depenses_par_poste.get(poste, 0.0)
        budget = budgets[poste]
        restant = budget - depense
        st.metric(label=f"{poste}", value=f"Dépensé : {depense:.2f} €", delta=f"Reste : {restant:.2f} €", delta_color="inverse" if restant < 0 else "normal")

    # Affichage graphique des dépenses par poste
    st.bar_chart(depenses_par_poste)

    # Calcul de la différence entre le revenu et les dépenses totales
    difference_revenu_depense = revenu - total_depenses
    st.subheader("Solde du mois")
    st.metric(label="Revenu - Dépenses", value=f"{difference_revenu_depense:.2f} €", delta_color="normal" if difference_revenu_depense >= 0 else "inverse")

else:
    st.write("Aucune transaction enregistrée pour le mois sélectionné.")