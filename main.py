import requests
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import urllib.parse

def login_and_get_token(email, password, code_2fa):
    try:
        driver = webdriver.Chrome()
        driver.get("https://www.facebook.com")
        
        # Login
        email_input = driver.find_element(By.ID, "email")
        password_input = driver.find_element(By.ID, "pass")
        email_input.send_keys(email)
        password_input.send_keys(password)
        password_input.submit()

        # Wait for 2FA input if needed
        if code_2fa:
            try:
                approvals_code = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "approvals_code")))
                approvals_code.send_keys(code_2fa)
                approvals_code.submit()
            except:
                pass

        # Navigate to developers page
        driver.get("https://developers.facebook.com")
        time.sleep(5)  # Wait for page load
        
        # Get cookies and extract access token
        cookies = driver.get_cookies()
        access_token = None
        for cookie in cookies:
            if 'access_token' in cookie['name']:
                access_token = cookie['value']
                break
        
        driver.quit()
        return access_token
    except Exception as e:
        messagebox.showerror("خطأ", f"خطأ في تسجيل الدخول: {e}")
        return None

def print_instructions():
    messagebox.showinfo("تعليمات الاستخدام", """
1. قم بزيارة https://developers.facebook.com
2. قم بتسجيل الدخول وإنشاء تطبيق جديد
3. احصل على Access Token للصفحة مع الصلاحيات التالية:
   - pages_messaging
   - pages_read_engagement
   - pages_show_list
4. قم بنسخ Access Token وإدخاله عند الطلب
""")

def show_copyable_error(title, error_message):
    error_window = tk.Toplevel()
    error_window.title(title)
    error_window.geometry("500x300")
    
    text_widget = tk.Text(error_window, wrap=tk.WORD)
    text_widget.pack(expand=True, fill='both', padx=10, pady=10)
    text_widget.insert('1.0', str(error_message))
    
    copy_button = ttk.Button(error_window, text="نسخ", 
                            command=lambda: root.clipboard_append(text_widget.get('1.0', tk.END)))
    copy_button.pack(pady=5)

class MessengerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Facebook Messenger Sender")
        self.stop_fetching = False
        self.page_tokens = {}  # Move page_tokens to instance variable
        self.setup_ui()
        self.setup_error_window()
        
    def setup_ui(self):
        # Create main frames
        left_frame = ttk.Frame(self.root)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        right_frame = ttk.Frame(self.root)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Access Token Frame
        token_frame = ttk.LabelFrame(left_frame, text="Access Token")
        token_frame.pack(fill=tk.X, pady=5)
        
        token_buttons_frame = ttk.Frame(token_frame)
        token_buttons_frame.pack(fill=tk.X, padx=5)
        
        self.access_token_entry = ttk.Entry(token_frame, width=50)
        self.access_token_entry.pack(padx=5, pady=5)
        
        ttk.Button(token_buttons_frame, text="لصق", command=self.paste_token).pack(side=tk.LEFT, padx=2)
        ttk.Button(token_buttons_frame, text="حفظ", command=self.save_token).pack(side=tk.LEFT, padx=2)
        ttk.Button(token_buttons_frame, text="تحميل", command=self.load_token).pack(side=tk.LEFT, padx=2)
        
        # Pages Frame
        pages_frame = ttk.LabelFrame(left_frame, text="الصفحات")
        pages_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.pages_list = tk.Listbox(pages_frame, width=50, height=10)
        self.pages_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        pages_scrollbar = ttk.Scrollbar(pages_frame, orient=tk.VERTICAL, command=self.pages_list.yview)
        pages_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.pages_list.config(yscrollcommand=pages_scrollbar.set)
        
        ttk.Button(left_frame, text="استرجاع الصفحات", command=self.get_pages_gui).pack(pady=5)

        # Conversations Frame
        conv_frame = ttk.LabelFrame(right_frame, text="المحادثات")
        conv_frame.pack(fill=tk.BOTH, expand=True)
        
        self.conversations_list = tk.Listbox(conv_frame, width=50, height=10, selectmode=tk.EXTENDED)
        self.conversations_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        conv_scrollbar = ttk.Scrollbar(conv_frame, orient=tk.VERTICAL, command=self.conversations_list.yview)
        conv_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.conversations_list.config(yscrollcommand=conv_scrollbar.set)
        
        # Add buttons frame for conversation list management
        conv_buttons_frame = ttk.Frame(conv_frame)
        conv_buttons_frame.pack(fill=tk.X, pady=5)

        ttk.Button(conv_buttons_frame, text="إضافة معرف", command=self.add_id).pack(side=tk.LEFT, padx=2)
        ttk.Button(conv_buttons_frame, text="حذف المحدد", command=self.delete_selected_id).pack(side=tk.LEFT, padx=2)
        ttk.Button(conv_buttons_frame, text="تعديل المحدد", command=self.edit_selected_id).pack(side=tk.LEFT, padx=2)
        ttk.Button(conv_buttons_frame, text="تحديد الكل", command=self.select_all_ids).pack(side=tk.LEFT, padx=2)
        ttk.Button(conv_buttons_frame, text="تحديد المدى", command=self.select_range_ids).pack(side=tk.LEFT, padx=2)
        ttk.Button(conv_buttons_frame, text="إلغاء التحديد", command=self.clear_selection).pack(side=tk.LEFT, padx=2)
        ttk.Button(conv_buttons_frame, text="لصق المعرفات", command=self.paste_ids).pack(side=tk.LEFT, padx=2)

        # Counter and Controls Frame
        controls_frame = ttk.Frame(right_frame)
        controls_frame.pack(fill=tk.X, pady=5)
        
        self.counter_label = ttk.Label(controls_frame, text="عدد المراسلين: 0")
        self.counter_label.pack(side=tk.LEFT, padx=5)
        
        self.fetch_button = ttk.Button(controls_frame, text="بدء السحب", command=self.start_fetching)
        self.fetch_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(controls_frame, text="إيقاف", command=self.stop_fetching_process)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Message Frame
        message_frame = ttk.LabelFrame(right_frame, text="الرسالة")
        message_frame.pack(fill=tk.X, pady=5)
        
        self.message_entry = ttk.Entry(message_frame, width=50)
        self.message_entry.pack(padx=5, pady=5)
        
        ttk.Button(right_frame, text="إرسال للكل", command=self.send_to_all).pack(pady=5)
        ttk.Button(right_frame, text="حفظ المعرفات", command=self.save_ids).pack(pady=5)

    def setup_error_window(self):
        self.error_window = None

    def show_error_window(self, title, error_message):
        if self.error_window:
            self.error_window.destroy()
        
        self.error_window = tk.Toplevel(self.root)
        self.error_window.title(title)
        self.error_window.geometry("500x300")
        
        error_text = tk.Text(self.error_window, wrap=tk.WORD)
        error_text.pack(expand=True, fill='both', padx=5, pady=5)
        error_text.insert('1.0', str(error_message))
        
        copy_button = ttk.Button(
            self.error_window, 
            text="نسخ الخطأ", 
            command=lambda: self.root.clipboard_append(error_text.get('1.0', tk.END))
        )
        copy_button.pack(pady=5)

    def paste_token(self):
        try:
            clipboard_text = self.root.clipboard_get()
            self.access_token_entry.delete(0, tk.END)
            self.access_token_entry.insert(0, clipboard_text)
        except:
            messagebox.showerror("خطأ", "لا يوجد نص في الحافظة")

    def save_token(self):
        token = self.access_token_entry.get().strip()
        if not token:
            messagebox.showerror("خطأ", "لا يوجد توكن للحفظ")
            return
            
        try:
            with open('token.txt', 'w', encoding='utf-8') as f:
                f.write(token)
            messagebox.showinfo("تم", "تم حفظ التوكن بنجاح")
        except Exception as e:
            messagebox.showerror("خطأ", f"خطأ في حفظ التوكن: {str(e)}")

    def load_token(self):
        try:
            if os.path.exists('token.txt'):
                with open('token.txt', 'r', encoding='utf-8') as f:
                    token = f.read().strip()
                    self.access_token_entry.delete(0, tk.END)
                    self.access_token_entry.insert(0, token)
                messagebox.showinfo("تم", "تم تحميل التوكن بنجاح")
            else:
                messagebox.showinfo("تنبيه", "لا يوجد ملف توكن محفوظ")
        except Exception as e:
            messagebox.showerror("خطأ", f"خطأ في تحميل التوكن: {str(e)}")

    def start_fetching(self):
        self.stop_fetching = False
        threading.Thread(target=self.fetch_conversations_thread).start()
        self.fetch_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

    def stop_fetching_process(self):
        self.stop_fetching = True
        self.fetch_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def fetch_conversations_thread(self):
        """Fetch conversation IDs that start with 't' from the selected page"""
        selected_page = self.pages_list.get(tk.ACTIVE)
        if not selected_page:
            messagebox.showerror("خطأ", "الرجاء تحديد صفحة")
            self.fetch_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            return

        page_id = selected_page.split('(')[1][:-1]
        
        try:
            next_url = f'https://graph.facebook.com/v18.0/{page_id}/conversations'
            params = {
                'access_token': self.page_tokens.get(page_id),
                'fields': 'id,participants',  # Include participants to get thread info
                'limit': 50
            }
            
            count = 0
            while next_url and not self.stop_fetching:
                response = requests.get(next_url, params=params)
                data = response.json()
                
                for conv in data.get('data', []):
                    if self.stop_fetching:
                        break
                        
                    thread_id = conv.get('id')
                    # Check if the thread ID starts with 't_'
                    if thread_id and str(thread_id).startswith('t_'):
                        # Add thread ID to list if not already present
                        if thread_id not in self.conversations_list.get(0, tk.END):
                            self.conversations_list.insert(tk.END, thread_id)
                            count += 1
                            self.counter_label.config(text=f"عدد المحادثات: {count}")
                            self.root.update()
                
                # Get next page URL if available
                next_url = data.get('paging', {}).get('next')
                
            if count > 0:
                messagebox.showinfo("تم", f"تم العثور على {count} محادثة")
            else:
                messagebox.showinfo("تنبيه", "لم يتم العثور على محادثات")
                    
        except Exception as e:
            self.show_error_window("خطأ في سحب المحادثات", str(e))
        
        finally:
            self.fetch_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.stop_fetching = False

    def save_ids(self):
        ids = self.conversations_list.get(0, tk.END)
        if not ids:
            messagebox.showinfo("تنبيه", "لا توجد معرفات للحفظ")
            return
            
        with open('messenger_ids.txt', 'w', encoding='utf-8') as f:
            for user_id in ids:
                f.write(f"{user_id}\n")
        messagebox.showinfo("تم", "تم حفظ المعرفات بنجاح")

    def send_to_all(self):
        message = self.message_entry.get().strip()
        if not message:
            messagebox.showerror("خطأ", "الرجاء إدخال رسالة")
            return
            
        selected_page = self.pages_list.get(tk.ACTIVE)
        if not selected_page:
            messagebox.showerror("خطأ", "الرجاء تحديد صفحة")
            return
            
        page_id = selected_page.split('(')[1][:-1]
        
        if not messagebox.askyesno("تأكيد", "هل تريد إرسال الرسالة للجميع؟"):
            return
            
        success_count = 0
        fail_count = 0
        for i in range(self.conversations_list.size()):
            user_id = self.conversations_list.get(i)
            if self.send_message(user_id, message, page_id):
                success_count += 1
            else:
                fail_count += 1
            self.root.update()
            
        messagebox.showinfo("النتيجة", f"تم الإرسال بنجاح: {success_count}\nفشل الإرسال: {fail_count}")

    def get_pages_gui(self):
        access_token = self.access_token_entry.get().strip()
        if not access_token:
            messagebox.showerror("خطأ", "لم يتم إدخال Access Token!")
            return

        pages = self.get_pages(access_token)
        if not pages:
            messagebox.showerror("خطأ", "لم يتم العثور على صفحات أو أن Access Token غير صالح.")
            return

        self.pages_list.delete(0, tk.END)
        for page in pages:
            self.pages_list.insert(tk.END, f"{page['name']} ({page['id']})")

    def get_pages(self, access_token):
        try:
            url = 'https://graph.facebook.com/v18.0/me/accounts'
            params = {
                'access_token': access_token
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            pages = response.json()['data']
            # Store page tokens in the instance dictionary
            self.page_tokens = {page['id']: page['access_token'] for page in pages}
            return pages
        except requests.exceptions.RequestException as e:
            error_details = str(e)
            if hasattr(e.response, 'json'):
                error_details += f"\n\nAPI Response:\n{str(e.response.json())}"
            self.show_error_window("خطأ في الاتصال", error_details)
            return None

    def get_conversations(self, page_id, access_token):
        try:
            # تأكد من وجود توكن الصفحة
            page_token = self.page_tokens.get(page_id)
            if not page_token:
                self.show_error_window("خطأ", "لم يتم العثور على توكن الصفحة")
                return None
                
            url = f'https://graph.facebook.com/v18.0/{page_id}/conversations'
            params = {
                'access_token': page_token,
                'fields': 'participants',  # تبسيط الحقول المطلوبة
                'limit': 50
            }
            
            # إضافة headers
            headers = {
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            error_details = f"URL: {url}\nParams: {params}\n\nError: {str(e)}"
            if hasattr(e.response, 'json'):
                error_details += f"\n\nAPI Response:\n{str(e.response.json())}"
            self.show_error_window("خطأ في الاتصال", error_details)
            return None

    def send_message(self, conv_id, message, page_id):
        try:
            page_token = self.page_tokens.get(page_id)
            if not page_token:
                self.show_error_window("خطأ", "لم يتم العثور على توكن الصفحة")
                return False

            # تشفير النص ليكون آمنًا في الرابط
            encoded_message = urllib.parse.quote(message)
            
            # استخدام نفس الطريقة تماماً كما في الكود الآخر
            url = f"https://graph.facebook.com/v2.8/{conv_id}?method=POST&message={encoded_message}&access_token={page_token}"
            
            # إرسال الطلب باستخدام GET كما في الكود الأصلي
            response = requests.get(url)
            
            # التحقق من النتيجة
            result = response.json()
            if "error" in result:
                error_details = f"""
URL: {url}
Status Code: {response.status_code}
Error Response: {result}
"""
                self.show_error_window("خطأ في إرسال الرسالة", error_details)
                return False
                
            return True
            
        except requests.exceptions.RequestException as e:
            error_details = f"URL: {url}\nError: {str(e)}"
            if hasattr(e.response, 'json'):
                error_details += f"\n\nAPI Response:\n{str(e.response.json())}"
            self.show_error_window("خطأ في إرسال الرسالة", error_details)
            return False

    def add_id(self):
        """إضافة معرف جديد إلى قائمة المحادثات"""
        dialog = tk.Toplevel(self.root)
        dialog.title("إضافة معرف")
        dialog.geometry("300x100")
        
        ttk.Label(dialog, text="أدخل معرف المحادثة:").pack(pady=5)
        entry = ttk.Entry(dialog, width=40)
        entry.pack(pady=5)
        
        def submit():
            thread_id = entry.get().strip()
            if thread_id:
                # التأكد من أن المعرف يبدأ بـ 't_'
                if not thread_id.startswith('t_'):
                    thread_id = 't_' + thread_id
                
                # إضافة المعرف إلى القائمة
                self.conversations_list.insert(tk.END, thread_id)
                # تحديث العداد
                self.counter_label.config(text=f"عدد المحادثات: {self.conversations_list.size()}")
                dialog.destroy()
        
        ttk.Button(dialog, text="إضافة", command=submit).pack(pady=5)

    def delete_selected_id(self):
        """حذف المعرفات المحددة"""
        selection = self.conversations_list.curselection()
        if not selection:
            messagebox.showwarning("تنبيه", "الرجاء تحديد معرف للحذف")
            return
        if messagebox.askyesno("تأكيد الحذف", f"هل أنت متأكد من حذف {len(selection)} معرف محدد؟"):
            # الحذف بترتيب عكسي لتجنب مشاكل الترقيم
            for index in sorted(selection, reverse=True):
                self.conversations_list.delete(index)
            # تحديث العداد
            self.counter_label.config(text=f"عدد المحادثات: {self.conversations_list.size()}")

    def edit_selected_id(self):
        """Edit the selected ID"""
        selection = self.conversations_list.curselection()
        if not selection:
            messagebox.showwarning("تنبيه", "الرجاء تحديد معرف للتعديل")
            return
        if len(selection) > 1:
            messagebox.showwarning("تنبيه", "الرجاء تحديد معرف واحد للتعديل")
            return
        current_id = self.conversations_list.get(selection[0])
        dialog = tk.Toplevel(self.root)
        dialog.title("تعديل معرف")
        dialog.geometry("300x100")
        
        ttk.Label(dialog, text="عدل المعرف:").pack(pady=5)
        entry = ttk.Entry(dialog, width=40)
        entry.insert(0, current_id)
        entry.pack(pady=5)
        
        def submit():
            new_id = entry.get().strip()
            if new_id:
                self.conversations_list.delete(selection[0])
                self.conversations_list.insert(selection[0], new_id)
                dialog.destroy()
        
        ttk.Button(dialog, text="حفظ", command=submit).pack(pady=5)

    def select_all_ids(self):
        """تحديد كل المعرفات"""
        self.conversations_list.selection_set(0, tk.END)

    def clear_selection(self):
        """إلغاء تحديد كل المعرفات"""
        self.conversations_list.selection_clear(0, tk.END)

    def select_range_ids(self):
        """تحديد مدى من المعرفات"""
        dialog = tk.Toplevel(self.root)
        dialog.title("تحديد مدى")
        dialog.geometry("300x150")
        
        ttk.Label(dialog, text="من:").pack(pady=5)
        start_entry = ttk.Entry(dialog, width=40)
        start_entry.pack(pady=5)
        
        ttk.Label(dialog, text="إلى:").pack(pady=5)
        end_entry = ttk.Entry(dialog, width=40)
        end_entry.pack(pady=5)
        
        def submit():
            try:
                start = int(start_entry.get())
                end = int(end_entry.get())
                total_items = self.conversations_list.size()
                if 0 <= start <= end < total_items:
                    self.conversations_list.selection_clear(0, tk.END)
                    self.conversations_list.selection_set(start, end)
                    dialog.destroy()
                else:
                    messagebox.showerror("خطأ", f"الرجاء إدخال أرقام بين 0 و {total_items-1}")
            except ValueError:
                messagebox.showerror("خطأ", "الرجاء إدخال أرقام صحيحة")
        
        ttk.Button(dialog, text="تحديد", command=submit).pack(pady=5)

    def clear_selection(self):
        self.conversations_list.select_clear(0, tk.END)

    def paste_ids(self):
        """لصق معرفات من الحافظة وإضافتها إلى القائمة"""
        try:
            # الحصول على النصوص من الحافظة
            clipboard_text = self.root.clipboard_get()
            # تقسيم النصوص إلى أسطر
            ids = clipboard_text.splitlines()
            added_count = 0

            for thread_id in ids:
                thread_id = thread_id.strip()
                if thread_id:
                    # التأكد من أن المعرف يبدأ بـ 't_'
                    if not thread_id.startswith('t_'):
                        thread_id = 't_' + thread_id
                    
                    # إضافة المعرف إلى القائمة إذا لم يكن موجودًا بالفعل
                    if thread_id not in self.conversations_list.get(0, tk.END):
                        self.conversations_list.insert(tk.END, thread_id)
                        added_count += 1

            # تحديث العداد
            self.counter_label.config(text=f"عدد المحادثات: {self.conversations_list.size()}")
            messagebox.showinfo("تم", f"تم لصق {added_count} معرف جديد.")
        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ أثناء لصق المعرفات: {e}")

# دالة لإرسال رسالة إلى مراسل
def send_message(user_id, message, access_token):
    try:
        url = 'https://graph.facebook.com/v18.0/me/messages'
        params = {
            'access_token': access_token
        }
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            'recipient': {'id': user_id},
            'message': {'text': message}
        }
        response = requests.post(url, params=params, headers=headers, json=data)
        response.raise_for_status()
        messagebox.showinfo("نجاح", f"تم إرسال الرسالة بنجاح إلى المستخدم {user_id}!")
    except requests.exceptions.RequestException as e:
        if hasattr(e.response, 'json'):
            messagebox.showerror("خطأ", f"تفاصيل الخطأ: {e.response.json()}")
        else:
            messagebox.showerror("خطأ", f"خطأ في إرسال الرسالة: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = MessengerApp(root)
    root.mainloop()
