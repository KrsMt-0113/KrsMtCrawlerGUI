# 2025.9.10 @ KrsMt
# version: 4.0
# 采用图形界面，支持多实体查询,支持保存结果到指定文件

import time
import requests
import csv
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import threading

def extract_hot_wallet(addr_info, target, name):
    if (
        addr_info.get('arkhamEntity', {}).get('name') == name and
        addr_info.get('arkhamLabel', {}).get('name') == 'Hot Wallet'
    ):
        address = addr_info['address']
        chain = addr_info.get('chain')
        label = addr_info['arkhamLabel']['name']
        arkm_url = f"https://intel.arkm.com/explorer/address/{address}"

        key = f"{address}@{chain}"
        target[key] = {
            'chain': chain,
            'address': address,
            'arkm_url': arkm_url,
            'label': label
        }

def fetch_chain_data(chain, entity, num, headers, Entity, offset_limit):
    merged_result = {}
    limit = num
    try:
        for i in range(offset_limit):
            offset = i * limit
            time.sleep(1)
            url = "https://api.arkhamintelligence.com/transfers"
            querystring = {
                "base": entity,
                "chains": chain,
                "flow": "out",
                "limit": limit,
                "offset": offset,
                "sortKey": "time",
                "sortDir": "desc",
                "usdGte": 1,
            }
            response = requests.get(url, headers=headers, params=querystring)
            transfers = response.json().get('transfers')
            if not transfers:
                break
            for tx in transfers:
                if tx.get('fromAddressOwner'):
                    extract_hot_wallet(tx.get('fromAddressOwner', {}), merged_result, Entity)
                else:
                    extract_hot_wallet(tx.get('fromAddress', {}), merged_result, Entity)
        return chain, merged_result
    except Exception as e:
        print(f"[{Entity}] {chain} Failed：{e}")
        return chain, None

def entity_search(queryString, headers):
    searchUrl = "https://api.arkm.com/intelligence/search?query="
    searchResponse = requests.get(searchUrl + queryString, headers=headers)
    entities = searchResponse.json().get('arkhamEntities', [])
    return entities

def main_gui():
    try:
        resp = requests.get("https://api.arkm.com/health", timeout=5)
        if resp.status_code != 200 or resp.text.strip().lower() != "ok":
            tk.messagebox.showerror("Connection Error", f"Arkham API health check failed: {resp.text.strip()}")
            return
    except Exception as e:
        tk.messagebox.showerror("Connection Error", f"Failed to connect: {e}")
        return

    Chain = [
        'bitcoin',
        'ethereum',
        'solana',
        'tron',
        'dogecoin',
        'ton',
        'base',
        'arbitrum_one',
        'sonic',
        'optimism',
        'mantle',
        'avalanche',
        'bsc',
        'linea',
        'polygon',
        'blast',
        'manta',
        'flare'
    ]

    headers = {
        "API-Key": "Your_api_key"
    }

    root = tk.Tk()
    root.title("Arkm Hot Wallet Crawler @ KrsMt")
    tk.Label(root, text="Limit:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
    limit_entry = tk.Entry(root)
    limit_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

    tk.Label(root, text="Offset:").grid(row=1, column=0, sticky="e", padx=5, pady=2)
    offset_entry = tk.Entry(root)
    offset_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=2)

    tk.Label(root, text="Search:").grid(row=2, column=0, sticky="e", padx=5, pady=2)
    query_entry = tk.Entry(root)
    query_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=2)

    result_list = tk.Listbox(root, height=6)
    result_list.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=2)

    status_label = tk.Label(root, text="KrsMt @ 2025.9")
    status_label.grid(row=5, column=0, columnspan=2)

    progress = ttk.Progressbar(root, length=300)
    progress.grid(row=4, column=0, columnspan=2)

    root.grid_columnconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=1)

    def update_ui(val, msg):
        progress["value"] = val
        status_label.config(text=msg)

    def start_query():
        nonlocal num, offset_limit
        try:
            num = int(limit_entry.get())
            offset_limit = int(offset_entry.get())
        except ValueError:
            status_label.config(text="Invalid limit or offset")
            return
        q = query_entry.get().strip()
        result_list.delete(0, tk.END)
        ents = entity_search(q, headers)
        if not ents:
            status_label.config(text="No entities found. Try again.")
            return
        for idx, ent in enumerate(ents):
            result_list.insert(tk.END, f"{ent.get('name')} ({ent.get('type')})")
        # Store entities for selection
        result_list.entities = ents
        status_label.config(text=f"{len(ents)} entities found")

    def run_crawler(ent):
        def task():
            nonlocal num, offset_limit
            selectedEntityName = ent.get('name')
            selectedEntityId = ent.get('id')
            completed = {}
            count = 0
            total = len(Chain)
            progress["value"] = 0
            status_label.config(text="Starting...")
            all_results = []
            for ch in Chain:
                _, partial = fetch_chain_data(ch, selectedEntityId, num, headers, selectedEntityName, offset_limit)
                if partial:
                    completed[ch] = len(partial)
                    count += len(partial)
                    all_results.extend(partial.values())
                root.after(0, update_ui, progress["value"] + (100/total), f"<{ch}> {len(partial) if partial else 0} addresses found (total: {count})")
            summary = "\n".join([f"{c}: {n}" for c, n in completed.items()])
            file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
            if file_path:
                try:
                    with open(file_path, mode="w", encoding="utf-8", newline="") as f:
                        fieldnames = ['chain', 'address', 'arkm_url', 'label']
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(all_results)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save file: {e}")
            messagebox.showinfo("Result Summary", f"{summary}\nTotal: {count}")
            status_label.config(text="Waiting for next action...")
            progress["value"] = 0
        threading.Thread(target=task).start()

    def confirm_selection():
        sel = result_list.curselection()
        if not sel:
            messagebox.showwarning("Warning", "No entity selected.")
            return
        index = sel[0]
        ent = result_list.entities[index]
        if messagebox.askyesno("Confirm", f"Run crawler for {ent.get('name')}?"):
            run_crawler(ent)

    search_button = tk.Button(root, text="Search", command=start_query)
    confirm_button = tk.Button(root, text="Confirm", command=confirm_selection)

    root.grid_columnconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=1)

    search_button.grid(row=6, column=0, sticky="ew", padx=5, pady=5)
    confirm_button.grid(row=6, column=1, sticky="ew", padx=5, pady=5)

    root.mainloop()

if __name__ == "__main__":
    main_gui()
