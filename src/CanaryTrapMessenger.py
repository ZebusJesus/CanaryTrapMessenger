import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel
import random
import gnupg
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
import base64
import os
import getpass

words_to_replace = {
    "confidential": ["secret", "private", "classified"],
    "project": ["task", "assignment", "initiative"],
    "deadline": ["due date", "completion date", "target date"]
}

def generate_canary_trap_message(base_message, recipient_id):
    modified_message = base_message
    for word, alternatives in words_to_replace.items():
        if word in modified_message:
            alternative_word = alternatives[recipient_id % len(alternatives)]
            modified_message = modified_message.replace(word, alternative_word)
    return modified_message

def encrypt_message(message, recipient_email, sign_key=None):
    gpg = gnupg.GPG()
    if sign_key:
        encrypted_data = gpg.encrypt(message, recipient_email, sign=sign_key)
    else:
        encrypted_data = gpg.encrypt(message, recipient_email)
    return str(encrypted_data)

def derive_key(password, salt):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def encrypt_master_file(master_file_content, password):
    salt = os.urandom(16)
    key = derive_key(password, salt)
    cipher_suite = Fernet(key)
    encrypted_master_content = cipher_suite.encrypt(master_file_content.encode())
    return salt + encrypted_master_content

def decrypt_master_file(encrypted_master_content, password):
    salt = encrypted_master_content[:16]
    encrypted_content = encrypted_master_content[16:]
    key = derive_key(password, salt)
    cipher_suite = Fernet(key)
    decrypted_content = cipher_suite.decrypt(encrypted_content)
    return decrypted_content.decode()

def select_recipients_file():
    file_path = filedialog.askopenfilename(title="Select Recipients File")
    recipients_file_entry.delete(0, tk.END)
    recipients_file_entry.insert(0, file_path)

def import_public_key():
    key_file_path = filedialog.askopenfilename(title="Select Public Key File")
    if key_file_path:
        gpg = gnupg.GPG()
        with open(key_file_path, 'r') as key_file:
            key_data = key_file.read()
            import_result = gpg.import_keys(key_data)
            if import_result.count == 1:
                messagebox.showinfo("Success", "Public key imported successfully.")
            else:
                messagebox.showerror("Error", "Failed to import public key.")

def select_private_key():
    global private_key_path
    private_key_path = filedialog.askopenfilename(title="Select Private Key File")
    if private_key_path:
        messagebox.showinfo("Success", "Private key selected successfully.")

def show_replacements():
    replacements_window = Toplevel(root)
    replacements_window.title("Word Replacements")
    
    text = tk.Text(replacements_window, width=50, height=10, wrap=tk.WORD)
    text.pack(padx=10, pady=10)
    
    for word, alternatives in words_to_replace.items():
        text.insert(tk.END, f"{word}: {', '.join(alternatives)}\n")

def encrypt_messages():
    base_message = base_message_text.get("1.0", tk.END).strip()
    password = password_entry.get()
    recipients_file = recipients_file_entry.get()
    
    with open(recipients_file, 'r') as file:
        recipients = [line.strip().split(',') for line in file]

    master_file_content = ""
    for recipient_name, recipient_id, recipient_email in recipients:
        recipient_id = int(recipient_id)
        modified_message = generate_canary_trap_message(base_message, recipient_id)
        
        unencrypted_filename = f"unencrypted_message_recipient_{recipient_name}.txt"
        with open(unencrypted_filename, 'w') as unencrypted_file:
            unencrypted_file.write(f"Original message: {base_message}\n")
            unencrypted_file.write(f"Unencrypted message for {recipient_name} (ID: {recipient_id}): {modified_message}\n")
        
        encrypted_message = encrypt_message(modified_message, recipient_email, sign_key=private_key_path)
        
        encrypted_filename = f"encrypted_message_recipient_{recipient_name}.txt"
        with open(encrypted_filename, 'w') as encrypted_file:
            encrypted_file.write(f"Encrypted message for {recipient_name} (ID: {recipient_id}):\n{encrypted_message}\n")
        
        master_file_content += f"Original message: {base_message}\n"
        master_file_content += f"Unencrypted message for {recipient_name} (ID: {recipient_id}): {modified_message}\n"
        master_file_content += f"Encrypted message for {recipient_name} (ID: {recipient_id}):\n{encrypted_message}\n\n"

    encrypted_master_content = encrypt_master_file(master_file_content, password)
    with open("master_file.txt", 'wb') as master_file:
        master_file.write(encrypted_master_content)
    
    messagebox.showinfo("Success", "Messages have been encrypted and saved.")

def decrypt_master():
    password = password_entry.get()
    master_file = filedialog.askopenfilename(title="Select Master File")
    
    with open(master_file, 'rb') as file:
        encrypted_master_content = file.read()
    
    try:
        decrypted_master_content = decrypt_master_file(encrypted_master_content, password)
        with open("decrypted_master_file.txt", 'w') as decrypted_file:
            decrypted_file.write(decrypted_master_content)
        messagebox.showinfo("Success", "Master file has been decrypted and saved.")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred during decryption: {e}")
        
# Define the edit_replacements function
def edit_replacements():
    def add_replacement():
        word = word_entry.get().strip()
        alternatives = alternatives_entry.get().strip().split(',')
        if word and alternatives:
            words_to_replace[word] = alternatives
            update_replacements_list()
            word_entry.delete(0, tk.END)
            alternatives_entry.delete(0, tk.END)

    def delete_replacement():
        selected_word = replacements_listbox.get(tk.ACTIVE)
        if selected_word:
            del words_to_replace[selected_word]
            update_replacements_list()

    def update_replacements_list():
        replacements_listbox.delete(0, tk.END)
        for word, alternatives in words_to_replace.items():
            replacements_listbox.insert(tk.END, f"{word}: {', '.join(alternatives)}")

    replacements_window = Toplevel(root)
    replacements_window.title("Edit Word Replacements")

    tk.Label(replacements_window, text="Word:").grid(row=0, column=0, padx=10, pady=10)
    word_entry = tk.Entry(replacements_window, width=30)
    word_entry.grid(row=0, column=1, padx=10, pady=10)

    tk.Label(replacements_window, text="Alternatives (comma-separated):").grid(row=1, column=0, padx=10, pady=10)
    alternatives_entry = tk.Entry(replacements_window, width=30)
    alternatives_entry.grid(row=1, column=1, padx=10, pady=10)

    add_button = tk.Button(replacements_window, text="Add/Update", command=add_replacement)
    add_button.grid(row=2, column=0, columnspan=2, padx=10, pady=10)

    delete_button = tk.Button(replacements_window, text="Delete", command=delete_replacement)
    delete_button.grid(row=3, column=0, columnspan=2, padx=10, pady=10)

    replacements_listbox = tk.Listbox(replacements_window, width=50, height=10)
    replacements_listbox.grid(row=4, column=0, columnspan=2, padx=10, pady=10)

    update_replacements_list()
    
def show_help():
    messagebox.showinfo("Help", "This is a canary trap message encryptor application.\n\n"
                                "1. Enter the base message. This message is then manipulated to be unquie for each user.\n"
                                "2. Enter the password. This password is used to encrypt the master output file that should be stored for records\n"
                                "3. Select the recipients file. This file is a text file that contains the name,ID,email@eamil.com of every user\n"
                                "the public key for each email address must be present in your keyring. Use Gpg4win on windows systems to install needed tools\n"
                                "4. Import the public key. This option allows you to import a keyfile on a system with gpg installed\n"
                                "5. Select the private key. This is the private key used to sign the message to prove you are the sender of the message\n"
                                "6. Click 'Encrypt Messages' to encrypt the messages.\n"
                                "7. Click 'Decrypt Master File' to decrypt the master file.\n"
                                "8. Use 'Edit Replacements' to manage word replacements.")

def create_menu_bar(root):
    menu_bar = tk.Menu(root)

    # File menu
    file_menu = tk.Menu(menu_bar, tearoff=0)
    file_menu.add_command(label="Open", command=select_recipients_file)
    file_menu.add_command(label="Save", command=lambda: messagebox.showinfo("Save", "Save functionality not implemented."))
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=root.quit)
    menu_bar.add_cascade(label="File", menu=file_menu)

    # Edit menu
    edit_menu = tk.Menu(menu_bar, tearoff=0)
    edit_menu.add_command(label="Edit Replacements", command=edit_replacements)
    menu_bar.add_cascade(label="Edit", menu=edit_menu)

    # Help menu
    help_menu = tk.Menu(menu_bar, tearoff=0)
    help_menu.add_command(label="Help", command=show_help)
    menu_bar.add_cascade(label="Help", menu=help_menu)

    root.config(menu=menu_bar)
        
    

# Create the main window
root = tk.Tk()
root.title("Canary Trap Message Encryptor")
# Create the menu bar
create_menu_bar(root)

# Create and place the widgets
tk.Label(root, text="Base Message:").grid(row=0, column=0, padx=10, pady=10)
base_message_text = tk.Text(root, width=50, height=10, wrap=tk.WORD)
base_message_text.grid(row=0, column=1, padx=10, pady=10)

tk.Label(root, text="Password:").grid(row=1, column=0, padx=10, pady=10)
password_entry = tk.Entry(root, show="*", width=50)
password_entry.grid(row=1, column=1, padx=10, pady=10)

tk.Label(root, text="Recipients File:").grid(row=2, column=0, padx=10, pady=10)
recipients_file_entry = tk.Entry(root, width=50)
recipients_file_entry.grid(row=2, column=1, padx=10, pady=10)
select_file_button = tk.Button(root, text="Browse", command=select_recipients_file)
select_file_button.grid(row=2, column=2, padx=10, pady=10)

import_key_button = tk.Button(root, text="Import Public Key", command=import_public_key)
import_key_button.grid(row=3, column=0, columnspan=3, padx=10, pady=10)

select_private_key_button = tk.Button(root, text="Select Private Key", command=select_private_key)
select_private_key_button.grid(row=3, column=2, columnspan=3, padx=10, pady=10)

show_replacements_button = tk.Button(root, text="Show Replacements", command=show_replacements)
show_replacements_button.grid(row=5, column=0, columnspan=3, padx=10, pady=10)

encrypt_button = tk.Button(root, text="Encrypt Messages", command=encrypt_messages)
encrypt_button.grid(row=5, column=2, columnspan=3, padx=10, pady=10)

decrypt_button = tk.Button(root, text="Decrypt Master File", command=decrypt_master)
decrypt_button.grid(row=7, column=0, columnspan=3, padx=10, pady=10)

edit_replacements_button = tk.Button(root, text="Edit Replacements", command=edit_replacements)
edit_replacements_button.grid(row=8, column=0, columnspan=3, padx=10, pady=10)
# Run the main loop
root.mainloop()