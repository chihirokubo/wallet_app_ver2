from tkinter import *
from tkinter import messagebox
from tkinter import filedialog
from tkinter.ttk import Button, Style
from tkinter import ttk
import binascii
import os
import json
import sys
import base64
import time
import pprint
import copy
import threading
import contextlib

from wallet import Transaction
from core.client_core import ClientCore as Core
import utils
from p2p.message_manager import (
    MSG_NEW_TRANSACTION, 
    MSG_REQUEST_FULL_CHAIN
)

class WalletApp_GUI(Frame):
    def __init__(self, parent, my_port, c_host, c_port):
        Frame.__init__(self, parent)
        self.parent = parent
        self.parent.protocol('WM_DELETE_WINDOW', self.quit)
        self.coin_balance = StringVar(self.parent, '0')
        self.c_core = None
        self.initWallet(my_port, c_host, c_port)
        self.setupGUI()

    def quit(self, event=None):
        # 終了
        self.c_core.shutdown()
        self.parent.destroy()

    def initWallet(self, my_port, c_host, c_port):
        print('wallet app is initializing')

        self.c_core = Core(my_port, c_host, c_port, self.update_callback)
        self.c_core.start()
        self.update_balance()
        self.update_blockchain_semaphore = threading.Semaphore(1)
        self.start_update_blockchain()

    def display_info(self, title, info):
        """
        ダイアログボックスにメッセージを表示
        """
        f = Tk()
        label = Label(f, text=title)
        label.pack()
        info_area = Text(f, width=70, height=50)
        info_area.insert(INSERT, info)
        info_area.pack()

    def update_callback(self):
        print('update blockchain was called')
        self.update_balance()

    def update_balance(self):
        balance = str(self.c_core.blockchain.calculate_total_amount(self.c_core.wallet.blockchain_address))
        self.coin_balance.set(balance)

    def create_menu(self):
        top = self.winfo_toplevel()
        self.menuBar = Menu(top)
        top['menu'] = self.menuBar

        self.subMenu = Menu(self.menuBar, tearoff=0)
        self.menuBar.add_cascade(label='Menu', menu=self.subMenu)
        self.subMenu.add_command(label='Show My Info', command=self.show_my_info)
        self.subMenu.add_command(label='Wallet Sync', command=self.sync_miner_wallet)
        self.subMenu.add_command(label='Update Blockchan', command=self.update_blockchain)
        self.subMenu.add_separator()
        self.subMenu.add_command(label='Quit', command=self.quit)

        self.subMenu2 = Menu(self.menuBar, tearoff=0)
        self.menuBar.add_cascade(label='Logs', menu=self.subMenu2)
        self.subMenu2.add_command(label='Show Blockchain', command=self.show_my_blockchain)

    def show_my_info(self):
        f = Tk()
        label = Label(f, text='My Info')
        label.pack()

        pub_key = self.c_core.wallet.private_key
        priv_key = self.c_core.wallet.public_key
        bc_address = self.c_core.wallet.blockchain_address
        
        pub_key_str = Label(f, text='public key')
        pub_key_str.pack()
        pub_key_info = Text(f, width=70, height=10)
        pub_key_info.insert(INSERT, pub_key)
        pub_key_info.pack()
        priv_key_str = Label(f, text='private key')
        priv_key_str.pack()
        priv_key_info = Text(f, width=70, height=10)
        priv_key_info.insert(INSERT, priv_key)
        priv_key_info.pack()
        bc_address_str = Label(f, text='blockchain address')
        bc_address_str.pack()
        bc_address_info = Text(f, width=70, height=5)
        bc_address_info.insert(INSERT, bc_address)
        bc_address_info.pack()

    def update_blockchain(self):
        self.c_core.send_req_full_chain()

    def start_update_blockchain(self):
        is_acquire = self.update_blockchain_semaphore.acquire(blocking=False)
        if is_acquire:
            with contextlib.ExitStack() as stack:
                stack.callback(self.update_blockchain_semaphore.release)
                self.update_blockchain()
                update_interval = 10
                loop = threading.Timer(update_interval, self.start_update_blockchain)
                loop.start()

    def sync_miner_wallet(self):
        print('sync miner wallet is called')
        self.c_core.send_req_key_info()

    def wallet_sync(self):
        f = Tk()
        label = Label(f, text='Wallet Sync')
        label.pack()

        lf0 = LabelFrame(f, text='public key')
        lf0.pack(side=TOP, fill='both', expand='yes',padx=7, pady=7)

        lf1 = LabelFrame(f, text='private key')
        lf1.pack(side=TOP, fill='both', expand='yes',padx=7, pady=7)

        lf2 = LabelFrame(f, text='blockchain address')
        lf2.pack(side=TOP, fill='both', expand='yes',padx=7, pady=7)

        lf3 = LabelFrame(f, text='')
        lf3.pack(side=TOP, fill='both', expand='yes',padx=7, pady=7)

        self.pub_key_box = Entry(lf0, bd=2)
        self.pub_key_box.grid(row=70,column=10,pady=5)
        self.priv_key_box = Entry(lf1, bd=2)
        self.priv_key_box.grid(row=70,column=10,pady=5)
        self.bc_address_box = Entry(lf2, bd=2)
        self.bc_address_box.grid(row=70,column=10,pady=5)
        self.exec_button = Button(lf3, text='実行', command=self.button_func)
        self.exec_button.grid(row=6, column=1,sticky='NSEW')
        
    def button_func(self):
        pub_key = self.pub_key_box.get()
        priv_key = self.priv_key_box.get()
        bc_address = self.bc_address_box.get()
        # TODO 本当はwalletを更新したい(暗号インスタンスの復元)
        self.pub_key = pub_key
        self.priv_key = priv_key
        self.bc_address = bc_address


    def show_my_blockchain(self):
        """
        ノードのブロックチェーンを表示
        """
        mychain = self.c_core.get_my_blockchain()
        if mychain:
            mychain_str = pprint.pformat(mychain, indent=2)
            self.display_info('Current Blockchain', mychain_str)
        else:
            self.display_info('Warning', 'blockchain is empty!!')


    def setupGUI(self):
        self.parent.bind('<Control-q>', self.quit)
        self.parent.title('WalletAPP GUI')
        self.pack(fill = BOTH, expand=1)

        self.create_menu()

        lf = LabelFrame(self, text='Current Balance')
        lf.pack(side=TOP, fill='both', expand='yes', padx=7, pady=7)

        lf2 = LabelFrame(self, text='Recipient Address')
        lf2.pack(side=TOP, fill='both', expand='yes', padx=7, pady=7)

        lf3 = LabelFrame(self,text='Amount pay')
        lf3.pack(side=TOP, fill='both', expand='yes', padx=7, pady=7)

        lf4 = LabelFrame(self, text='')
        lf4.pack(side=TOP, fill='both', expand='yes', padx=7, pady=7)

        #所持コインの総額表示領域のラベル
        self.balance = Label(lf, textvariable=self.coin_balance, font='Helvetica 20')
        self.balance.pack()

        #受信者となる相手の公開鍵
        self.label = Label(lf2, text='')
        self.label.grid(row=70,column=10, pady=5)

        self.recipient_address = Entry(lf2, bd=2)
        self.recipient_address.grid(row=70, column=10, pady=5)

        # 送金額
        self.label2 = Label(lf3, text='')
        self.label2.grid(row=1, pady=5)
    
        self.amountBox = Entry(lf3, bd=2)
        self.amountBox.grid(row=1, column=1, pady=5, sticky='NSEW')

        # 送金実行ボタン
        self.sendBtn = Button(lf4, text='\nSend Coin(s)\n', command=self.sendCoins)
        self.sendBtn.grid(row=6, column=1, sticky='NSEW')

    def sendCoins(self):
        sendAtp = self.amountBox.get()
        recipient_address = self.recipient_address.get()
        
        if not sendAtp:
            messagebox.showwarning('Warning', 'Please enter the Amount to pay')
            return
        elif len(recipient_address)<=1:
            messagebox.showwarning('Warning', 'Please enter the recipient address')
            return
        else:
            result = messagebox.askyesno('Confirmation', f'sending {sendAtp} coins to :\n{recipient_address}')

        if result:

            if float(sendAtp) > self.c_core.blockchain.calculate_total_amount(self.c_core.wallet.blockchain_address):
                messagebox.showwarning('short of coin', 'not enough coin to be sent')
                return

            transaction = Transaction(
                self.c_core.wallet.private_key,
                self.c_core.wallet.public_key,
                self.c_core.wallet.blockchain_address,
                recipient_address,
                sendAtp
            )
            msg = transaction.get_json_msg()
            self.c_core.send_new_transaction(msg)
        
        self.amountBox.delete(0,END)
        self.recipient_address.delete(0,END)
        self.update_balance()

def main(my_port, c_host, c_port):
    root = Tk()
    app = WalletApp_GUI(root, my_port, c_host, c_port)
    root.mainloop()

if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('--c_host', default=utils.get_host())
    parser.add_argument('--c_port', default=5001, type=int)
    parser.add_argument('-p', '--port', default=50001, type=int)

    args = parser.parse_args()
    c_host = args.c_host
    c_port = args.c_port
    port = args.port

    main(port, c_host, c_port)