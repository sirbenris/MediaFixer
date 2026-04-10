import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
import threading
import subprocess
import sys
import re
import platform
import urllib.request
import webbrowser
import json
import sv_ttk

import config
from config import current_config, texts, audio_flags as AUDIO_FLAGS
import media_engine

app = tk.Tk()
app.geometry("1100x900")
app.title(texts.get("app_title", "Media Fixer - Native Edition"))

sv_ttk.set_theme("dark")

# unbind comboboxes from mousewheel to prevent scrolling issues when hovering over them
app.unbind_class("TCombobox", "<MouseWheel>")
app.unbind_class("TCombobox", "<Button-4>")
app.unbind_class("TCombobox", "<Button-5>")

# Native scrollable frame wrapper
class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=0, bg="#202020")
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.window_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.window_id, width=e.width))

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

# Global state
lbl_status_main = None
lbl_version = None
btn_select_file = None
btn_select_folder = None
lbl_selected_file = None
scroll_table = None
var_save_mode = None

lbl_bulk_folder = None
var_bulk_ext = None
var_bulk_contains = None
var_bulk_case = None
var_bulk_sub = None
var_bulk_track = None
var_bulk_track_custom = None
entry_bulk_track_custom = None
var_bulk_skip = None

var_cond_lang_en = None
var_cond_lang_val = None
var_cond_codec_en = None
var_cond_codec_val = None
var_cond_bit_en = None
var_cond_bit_val = None

var_bulk_lang = None
var_bulk_codec = None
var_bulk_bit = None
var_bulk_chan = None
var_bulk_act = None
var_bulk_backup = None
var_bulk_title = None
var_bulk_clear_handler = None
btn_bulk_go = None
bulk_prog_bar = None
lbl_bulk_status = None
bulk_target_folder = ""

def check_for_updates():
    if config.APP_VERSION == "dev": return
    try:
        url = "https://api.github.com/repos/sirbenris/MediaFixer/releases/latest"
        req = urllib.request.Request(url, headers={'User-Agent': 'MediaFixer-Update-Check'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            latest_version = data.get("tag_name", "").replace("v", "")
            if latest_version and latest_version != config.APP_VERSION:
                # Update bottom right label to show available update and make it clickable
                app.after(0, lambda: lbl_version.configure(
                    text=f"v{config.APP_VERSION} (Update: v{latest_version}!)", 
                    foreground="#FF9800", cursor="hand2"
                ))
                app.after(0, lambda: lbl_version.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/sirbenris/MediaFixer/releases/latest")))
                
                app.after(1500, lambda v=latest_version: show_update_popup(v))
    except Exception as e: print(f"Update check failed: {e}")

def show_update_popup(new_version):
    msg = texts.get("update_msg", f"A new version ({new_version}) is available!\nDo you want to download it?").replace("{v}", new_version)
    if messagebox.askyesno(texts.get("update_title", "Update available!"), msg):
        webbrowser.open("https://github.com/sirbenris/MediaFixer/releases/latest")

def update_main_status():
    if not all([lbl_status_main, btn_select_file, btn_select_folder]): return False
    if media_engine.check_ffmpeg_installed():
        lbl_status_main.configure(text=texts.get("status_ready", "✅ FFmpeg Ready"), foreground="#4CAF50")
        btn_select_file.configure(state="normal")
        btn_select_folder.configure(state="normal")
        return True
    lbl_status_main.configure(text=texts.get("status_missing", "❌ FFmpeg Missing!"), foreground="#F44336")
    btn_select_file.configure(state="disabled")
    btn_select_folder.configure(state="disabled")
    return False

def on_language_changed(choice):
    if choice == current_config["ui_language"]: return
    current_config["ui_language"] = choice
    config.save_config()
    app.destroy()
    os.execl(sys.executable, sys.executable, *sys.argv)

def show_setup_wizard():
    wizard = tk.Toplevel(app)
    wizard.title("Media Fixer - Setup")
    wizard.geometry("600x500")
    wizard.attributes("-topmost", True)
    wizard.grab_set()
    
    ttk.Label(wizard, text="System-Check:", font=("Segoe UI", 16, "bold")).pack(pady=15)
    lbl_status = ttk.Label(wizard, text="Checking FFmpeg...")
    lbl_status.pack(pady=5)
    
    is_installed = media_engine.check_ffmpeg_installed()
    btn_save = ttk.Button(wizard, text="Finish & Start", state="disabled")

    def run_download():
        def task():
            success = media_engine.download_ffmpeg_windows(lambda msg: lbl_status.configure(text=msg))
            if success:
                lbl_status.configure(text="✅ FFmpeg installed successfully!", foreground="#4CAF50")
                btn_save.configure(state="normal")
                update_main_status()
            else:
                lbl_status.configure(text="❌ Download failed!", foreground="#F44336")
        threading.Thread(target=task, daemon=True).start()

    if is_installed:
        lbl_status.configure(text="✅ FFmpeg found!", foreground="#4CAF50")
        btn_save.configure(state="normal")
    else:
        if platform.system() == "Windows":
            lbl_status.configure(text="❌ FFmpeg missing on your system.", foreground="#F44336")
            btn_dl = ttk.Button(wizard, text="📥 Download FFmpeg (Portable)", command=run_download)
            btn_dl.pack(pady=10)
        else:
            cmd_hint = "sudo apt install ffmpeg" if platform.system() == "Linux" else "brew install ffmpeg"
            lbl_status.configure(text=f"❌ FFmpeg missing!\n\nPlease install it via terminal:\n{cmd_hint}", foreground="#FF9800")
            btn_recheck = ttk.Button(wizard, text="🔄 Re-Check", command=lambda: btn_save.configure(state="normal") if media_engine.check_ffmpeg_installed() else None)
            btn_recheck.pack(pady=10)
        
    ttk.Label(wizard, text="Default UI Language:").pack(pady=(20, 5))
    var_ui = tk.StringVar(value=config.available_languages[0])
    ttk.Combobox(wizard, values=config.available_languages, textvariable=var_ui, state="readonly").pack()
    
    def on_save_wizard():
        current_config["ui_language"] = var_ui.get()
        config.save_config()
        wizard.destroy()
        
    btn_save.configure(command=on_save_wizard)
    btn_save.pack(pady=30)

# Single file operations
def select_single_file():
    filepath = filedialog.askopenfilename(
        title=texts.get("dialog_title_video", "Select Video"),
        filetypes=[(texts.get("dialog_filter_video", "Video Files"), "*.mp4 *.mkv"), ("All Files", "*.*")]
    )
    if filepath: analyze_file(filepath)

def apply_audio_action(orig_path, target_path, a_idx, lang, codec, bitrate, channels, action, title_val, clear_handler, raw_codec, btn, total, duration, p_f, p_b, p_l, mode):
    def task():
        app.after(0, lambda: p_f.pack(side="top", fill="x", padx=10, pady=(0, 10)))
        app.after(0, lambda: btn.configure(state="disabled", text=texts.get("status_fixing", "Processing...")))
        
        out_file = f"{orig_path}.temp.mp4" if mode == "inline" else target_path
        cmd = [media_engine.FFMPEG_CMD, "-nostdin", "-i", orig_path, "-map", "0", "-c", "copy"]

        if action == "Delete": cmd += ["-map", f"-0:a:{a_idx}"]
        elif action == "Patch":
            c_val = codec.lower() if codec != "Copy" else "copy"
            # Force re-encode with original codec if 'copy' is selected but parameters are changed
            if c_val == "copy" and (bitrate != "Original" or channels != "Original"): c_val = raw_codec
            cmd += [f"-c:a:{a_idx}", c_val]
            if bitrate != "Original": cmd += [f"-b:a:{a_idx}", bitrate]
            if channels == "Stereo Downmix": cmd += [f"-ac:a:{a_idx}", "2"]
            cmd += [f"-metadata:s:a:{a_idx}", f"language={lang}"]
            cmd += [f"-metadata:s:a:{a_idx}", f"title={title_val}"]
            if clear_handler: cmd += [f"-metadata:s:a:{a_idx}", "handler_name="]
        elif action == "Add New":
            cmd += ["-map", f"0:a:{a_idx}"]
            c_val = codec.lower() if codec != "Copy" else "copy"
            if c_val == "copy" and (bitrate != "Original" or channels != "Original"): c_val = raw_codec
            cmd += [f"-c:a:{total}", c_val]
            if bitrate != "Original": cmd += [f"-b:a:{total}", bitrate]
            if channels == "Stereo Downmix": cmd += [f"-ac:a:{total}", "2"]
            cmd += [f"-metadata:s:a:{total}", f"language={lang}"]
            cmd += [f"-metadata:s:a:{total}", f"title={title_val}"]
            if clear_handler: cmd += [f"-metadata:s:a:{total}", "handler_name="]

        # --- SMART CPU LIMITER ---
            cpu_choice = var_bulk_cpu.get()
            if cpu_choice == texts.get("opt_cpu_med", "Medium"):
                cores = max(1, (os.cpu_count() or 4) // 2)
                cmd += ["-threads", str(cores)]
            elif cpu_choice == texts.get("opt_cpu_low", "Low"):
                cmd += ["-threads", "1"]   

        cmd += ["-ignore_unknown", "-dn", "-write_tmcd", "0", out_file, "-y"]

        try:
            cflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            process = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True, encoding='utf-8', errors='replace', creationflags=cflags)
            time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2}\.\d+)")
            
            for line in process.stderr:
                match = time_pattern.search(line)
                if match and duration > 0:
                    h, m, s = match.groups()
                    pct = min((int(h)*3600 + int(m)*60 + float(s)) / duration, 1.0)
                    app.after(0, lambda p=pct: (p_b.configure(value=p), p_l.configure(text=f"{int(p*100)}%")))
            process.wait()
            if process.returncode == 0:
                shutil.copystat(orig_path, out_file)
                if mode == "inline":
                    os.remove(orig_path)
                    os.rename(out_file, orig_path)
                app.after(0, lambda: btn.configure(text=texts.get("status_success", "✅ Done!")))
                app.after(1000, analyze_file, orig_path if mode == "inline" else target_path)
            else: raise Exception("FFmpeg error")
        except Exception as e:
            app.after(0, lambda: btn.configure(text=texts.get("status_failed", "❌ Error!"), state="normal"))
            if mode == "inline" and os.path.exists(out_file): os.remove(out_file)

    threading.Thread(target=task, daemon=True).start()

def on_go_clicked(filepath, a_idx, var_lang, var_codec, var_bit, var_chan, var_act, var_title, var_clear, raw_codec, btn, total, dur, p_f, p_b, p_l):
    mode = var_save_mode.get()
    target = filepath
    if mode == "newfile":
        target = filedialog.asksaveasfilename(title=texts.get("dialog_save_as", "Save As..."), initialfile=f"fixed_{os.path.basename(filepath)}", defaultextension=".mp4")
        if not target: return
    act_map_rev = {texts.get("btn_action_patch", "Patch"): "Patch", texts.get("btn_action_add", "Add New"): "Add New", texts.get("btn_action_delete", "Delete"): "Delete"}
    apply_audio_action(filepath, target, a_idx, AUDIO_FLAGS[var_lang.get()], var_codec.get(), var_bit.get(), var_chan.get(), act_map_rev[var_act.get()], var_title.get(), var_clear.get(), raw_codec, btn, total, dur, p_f, p_b, p_l, mode)

def analyze_file(filepath):
    for widget in scroll_table.scrollable_frame.winfo_children(): widget.destroy()
    lbl_selected_file.configure(text=texts.get("lbl_analyzing", "Analyzing..."), foreground="#FFEB3B")
    app.update()
    
    data = media_engine.probe_file(filepath)
    if not data:
        ttk.Label(scroll_table.scrollable_frame, text=texts.get("lbl_no_audio", "No Audio found.")).pack(pady=20)
        lbl_selected_file.configure(text=os.path.basename(filepath), foreground="white")
        return
        
    streams = data.get("streams", [])
    duration = float(data.get("format", {}).get("duration", 1.0))
    lbl_selected_file.configure(text=os.path.basename(filepath), foreground="white")
    act_map = {texts.get("btn_action_patch", "Patch"): "Patch", texts.get("btn_action_add", "Add New"): "Add New", texts.get("btn_action_delete", "Delete"): "Delete"}

    for a_idx, stream in enumerate(streams):
        tags = stream.get("tags", {})
        lang_orig = tags.get("language", "und")
        codec_orig = stream.get("codec_name", "unk").upper()
        raw_codec = stream.get("codec_name", "aac") 
        channels_orig = stream.get("channels", "?")
        bps = stream.get("bit_rate") or tags.get("BPS")
        bitrate_kbps = f"{int(bps)//1000} kbps" if str(bps).isdigit() else texts.get("unknown_bitrate", "???")
        track_title = tags.get("title", "")
        title_display = f" - '{track_title}'" if track_title else ""
        
        row = ttk.Frame(scroll_table.scrollable_frame, style="Card.TFrame")
        row.pack(fill="x", pady=5, padx=5)

        info_text = f"🎵 #{a_idx} | [{lang_orig}] | {codec_orig} | {bitrate_kbps} | {channels_orig} Ch{title_display}"
        ttk.Label(row, text=info_text, font=("Segoe UI", 10, "bold")).pack(side="top", anchor="w", padx=10, pady=5)
        
        ctrl = ttk.Frame(row)
        ctrl.pack(side="top", fill="x", padx=5, pady=2)

        v_lang = tk.StringVar(value=[k for k,v in AUDIO_FLAGS.items() if v == lang_orig][0] if lang_orig in AUDIO_FLAGS.values() else "English")
        ttk.Combobox(ctrl, values=config.available_flags, textvariable=v_lang, width=12, state="readonly").pack(side="left", padx=2)
        v_codec = tk.StringVar(value="Copy")
        ttk.Combobox(ctrl, values=config.CODEC_OPTIONS, textvariable=v_codec, width=8, state="readonly").pack(side="left", padx=2)
        v_bit = tk.StringVar(value="Original")
        ttk.Combobox(ctrl, values=config.BITRATE_OPTIONS, textvariable=v_bit, width=10, state="readonly").pack(side="left", padx=2)
        v_chan = tk.StringVar(value="Original")
        ttk.Combobox(ctrl, values=config.CHANNEL_OPTIONS, textvariable=v_chan, width=15, state="readonly").pack(side="left", padx=2)
        v_act = tk.StringVar(value=list(act_map.keys())[0])
        ttk.Combobox(ctrl, values=list(act_map.keys()), textvariable=v_act, width=15, state="readonly").pack(side="left", padx=2)

        ctrl2 = ttk.Frame(row)
        ctrl2.pack(side="top", fill="x", padx=5, pady=(5, 10))
        
        ttk.Label(ctrl2, text=texts.get("lbl_title", "Title:")).pack(side="left", padx=(2, 5))
        v_title = tk.StringVar(value=track_title)
        ttk.Entry(ctrl2, textvariable=v_title, width=30).pack(side="left", padx=2)
        
        v_clear = tk.BooleanVar(value=False)
        ttk.Checkbutton(ctrl2, text=texts.get("chk_clear_handler", "Clear Handler"), variable=v_clear).pack(side="left", padx=15)

        p_f = ttk.Frame(row)
        p_b = ttk.Progressbar(p_f, maximum=1.0, mode="determinate"); p_b.pack(side="left", fill="x", expand=True, padx=(0, 10))
        p_l = ttk.Label(p_f, text="0%", font=("Segoe UI", 9, "bold")); p_l.pack(side="right")

        btn_go = ttk.Button(ctrl, text="GO", style="Accent.TButton")
        btn_go.configure(command=lambda a=a_idx, l=v_lang, c=v_codec, b=v_bit, ch=v_chan, act=v_act, tit=v_title, clr=v_clear, rc=raw_codec, btn=btn_go, p_f=p_f, p_b=p_b, p_l=p_l: 
            threading.Thread(target=lambda: on_go_clicked(filepath, a, l, c, b, ch, act, tit, clr, rc, btn, len(streams), duration, p_f, p_b, p_l)).start()
        )
        btn_go.pack(side="right", padx=5)

# Bulk operations
def select_bulk_folder():
    global bulk_target_folder
    folder = filedialog.askdirectory(title=texts.get("btn_folder", "Select Folder"))
    if folder:
        bulk_target_folder = folder
        lbl_bulk_folder.configure(text=folder)

def on_track_sel_changed(event):
    if var_bulk_track.get() == texts.get("opt_track_custom", "Custom Track #"): entry_bulk_track_custom.configure(state="normal")
    else: entry_bulk_track_custom.configure(state="disabled")

def match_bulk_streams(filepath):
    data = media_engine.probe_file(filepath)
    if not data: return [], 0
    streams = data.get("streams", [])
    target_tracks = []
    track_sel = var_bulk_track.get()
    
    if track_sel == texts.get("opt_track_0", "Track #0"): target_tracks = [0]
    elif track_sel == texts.get("opt_track_1", "Track #1"): target_tracks = [1]
    elif track_sel == texts.get("opt_track_custom", "Custom Track #"):
        try: 
            val = var_bulk_track_custom.get().strip()
            if val.isdigit(): target_tracks = [int(val)]
        except: pass

    matched = []
    for a_idx, stream in enumerate(streams):
        if track_sel != texts.get("opt_all_audio", "All Audio") and a_idx not in target_tracks: continue
        tags = stream.get("tags", {})
        if var_cond_lang_en.get() and tags.get("language", "und") != AUDIO_FLAGS.get(var_cond_lang_val.get(), "und"): continue
        if var_cond_codec_en.get() and stream.get("codec_name", "unk").upper() != var_cond_codec_val.get(): continue
        if var_cond_bit_en.get():
            bps = stream.get("bit_rate") or tags.get("BPS")
            kbps = str(int(bps)//1000) if str(bps).isdigit() else ""
            target_bps = var_cond_bit_val.get().strip()
            if target_bps and target_bps != kbps: continue

        if var_bulk_skip.get() and var_bulk_act.get() == texts.get("btn_action_patch", "Patch"):
            already_lang = tags.get("language", "und") == AUDIO_FLAGS.get(var_bulk_lang.get(), "und")
            already_codec = (var_bulk_codec.get() == "Copy") or (stream.get("codec_name", "unk").upper() == var_bulk_codec.get().upper())
            already_title = (not var_bulk_title.get()) or (tags.get("title", "") == var_bulk_title.get())
            already_handler = (not var_bulk_clear_handler.get()) or ("handler_name" not in tags)
            if already_lang and already_codec and already_title and already_handler: continue

        matched.append(a_idx)
    return matched, len(streams)

def simulate_bulk_process():
    if not bulk_target_folder: 
        messagebox.showwarning(texts.get("warn_title", "Warning"), texts.get("warn_no_folder", "Please select a folder first!"))
        return
    if var_bulk_track.get() == texts.get("opt_all_audio", "All Audio Streams"):
        if not messagebox.askyesno(texts.get("warn_title", "Warning"), texts.get("warn_all_audio", "Modify EVERY matching track?")): return
    do_backup = var_bulk_backup.get()
    if not do_backup:
        if not messagebox.askyesno(texts.get("warn_title", "Warning"), texts.get("warn_msg", "Proceed without backups?")): return

    def task():
        app.after(0, lambda: btn_bulk_go.configure(state="disabled"))
        app.after(0, lambda: lbl_bulk_status.configure(text=texts.get("status_bulk_scan", "Scanning..."), foreground="#FFEB3B"))
        
        target_ext = var_bulk_ext.get()
        name_filter = var_bulk_contains.get()
        if not var_bulk_case.get(): name_filter = name_filter.lower()
        action = var_bulk_act.get()
        target_lang_code = AUDIO_FLAGS.get(var_bulk_lang.get(), "und")
        codec_val = var_bulk_codec.get()
        title_val = var_bulk_title.get()
        clear_handler = var_bulk_clear_handler.get()
        
        files_to_process = []
        if var_bulk_sub.get():
            for root, dirs, files in os.walk(bulk_target_folder):
                for f in files: files_to_process.append(os.path.join(root, f))
        else:
            for f in os.listdir(bulk_target_folder):
                filepath = os.path.join(bulk_target_folder, f)
                if os.path.isfile(filepath): files_to_process.append(filepath)

        filtered_files = []
        for f in files_to_process:
            ext = os.path.splitext(f)[1].lower()
            if target_ext in [".mp4", ".mkv"] and ext != target_ext: continue
            if target_ext not in [".mp4", ".mkv"] and ext not in [".mp4", ".mkv"]: continue
            fname_check = os.path.basename(f)
            if not var_bulk_case.get(): fname_check = fname_check.lower()
            if name_filter and name_filter not in fname_check: continue
            filtered_files.append(f)

        if not filtered_files:
            app.after(0, lambda: lbl_bulk_status.configure(text=texts.get("status_bulk_empty", "Empty"), foreground="#FF9800"))
            app.after(0, lambda: btn_bulk_go.configure(state="normal"))
            return

        app.after(0, lambda: bulk_prog_bar.configure(value=0))
        total_files = len(filtered_files)
        planned_changes = []

        for i, filepath in enumerate(filtered_files):
            matched_indices, total_audio = match_bulk_streams(filepath)
            if matched_indices:
                tracks_str = ", ".join(str(idx) for idx in matched_indices)
                if action == texts.get("btn_action_delete", "Delete"): desc = f"Delete Track(s) #{tracks_str}"
                else:
                    act_word = "Patch" if action == texts.get("btn_action_patch", "Patch") else "Add"
                    desc_parts = [f"{act_word} #{tracks_str} -> [{target_lang_code}]"]
                    if codec_val != "Copy": desc_parts.append(f"Codec: {codec_val}")
                    if title_val: desc_parts.append(f"Title: '{title_val}'")
                    if clear_handler: desc_parts.append("Clear Handler")
                    desc = " | ".join(desc_parts)
                planned_changes.append({"filepath": filepath, "desc": desc, "matched_indices": matched_indices, "total_audio": total_audio})
            app.after(0, lambda p=(i+1)/total_files: bulk_prog_bar.configure(value=p))

        app.after(0, lambda: show_simulation_popup(planned_changes))
        app.after(0, lambda: lbl_bulk_status.configure(text="Scan complete.", foreground="white"))
        app.after(0, lambda: btn_bulk_go.configure(state="normal"))

    threading.Thread(target=task, daemon=True).start()

def show_simulation_popup(planned_changes):
    if not planned_changes:
        messagebox.showinfo("Info", texts.get("status_bulk_empty", "Empty"))
        return
        
    sim_win = tk.Toplevel(app)
    sim_win.title(texts.get("win_sim_title", "Simulation"))
    sim_win.geometry("800x550")
    sim_win.grab_set()
    
    ttk.Label(sim_win, text=texts.get("lbl_sim_intro", "Planned changes:"), font=("Segoe UI", 16, "bold")).pack(pady=10)
    
    # Standard Tkinter Text widget since ttk doesn't have a multi-line text widget
    txt = tk.Text(sim_win, width=90, height=20, font=("Consolas", 10), bg="#252525", fg="#FFFFFF", relief="flat")
    txt.pack(padx=10, pady=10)
    for chg in planned_changes: txt.insert("end", f"[{chg['desc']}]  ->  {os.path.basename(chg['filepath'])}\n")
    txt.configure(state="disabled")
    
    btn_frame = ttk.Frame(sim_win)
    btn_frame.pack(pady=10)
    
    ttk.Button(btn_frame, text=texts.get("btn_sim_cancel", "Cancel"), command=sim_win.destroy).pack(side="left", padx=10)
    ttk.Button(btn_frame, text=texts.get("btn_sim_execute", "Execute Now!"), style="Accent.TButton", command=lambda: execute_bulk_process(planned_changes, sim_win)).pack(side="left", padx=10)

def execute_bulk_process(planned_changes, sim_win):
    sim_win.destroy()
    do_backup = var_bulk_backup.get()
    
    def task():
        app.after(0, lambda: btn_bulk_go.configure(state="disabled"))
        app.after(0, lambda: bulk_prog_bar.configure(value=0))
        
        total = len(planned_changes)
        successful_files = []
        
        for i, chg in enumerate(planned_changes):
            filepath = chg['filepath']
            desc = chg['desc']
            matched_indices = chg['matched_indices']
            total_audio = chg['total_audio']
            
            app.after(0, lambda d=desc, f=os.path.basename(filepath): lbl_bulk_status.configure(text=f"{d} : {f}"))
            
            file_data = media_engine.probe_file(filepath)
            streams = file_data.get("streams", []) if file_data else []
            target_lang_code = AUDIO_FLAGS.get(var_bulk_lang.get(), "und")
            action = var_bulk_act.get()
            title_val = var_bulk_title.get()
            clear_handler = var_bulk_clear_handler.get()
            
            out_file = f"{filepath}.temp.mp4"
            cmd = [media_engine.FFMPEG_CMD, "-nostdin", "-i", filepath, "-map", "0", "-c", "copy"]

            if action == texts.get("btn_action_delete", "Delete"):
                for t_idx in matched_indices: cmd += ["-map", f"-0:a:{t_idx}"]
            elif action == texts.get("btn_action_patch", "Patch"):
                for t_idx in matched_indices:
                    raw_codec = streams[t_idx].get("codec_name", "aac") if t_idx < len(streams) else "aac"
                    c_val = var_bulk_codec.get().lower() if var_bulk_codec.get() != "Copy" else "copy"
                    if c_val == "copy" and (var_bulk_bit.get() != "Original" or var_bulk_chan.get() != "Original"): c_val = raw_codec
                    cmd += [f"-c:a:{t_idx}", c_val]
                    if var_bulk_bit.get() != "Original": cmd += [f"-b:a:{t_idx}", var_bulk_bit.get()]
                    if var_bulk_chan.get() == "Stereo Downmix": cmd += [f"-ac:a:{t_idx}", "2"]
                    cmd += [f"-metadata:s:a:{t_idx}", f"language={target_lang_code}"]
                    if title_val: cmd += [f"-metadata:s:a:{t_idx}", f"title={title_val}"]
                    if clear_handler: cmd += [f"-metadata:s:a:{t_idx}", "handler_name="]
            elif action == texts.get("btn_action_add", "Add New"):
                for idx_offset, t_idx in enumerate(matched_indices):
                    new_idx = total_audio + idx_offset
                    raw_codec = streams[t_idx].get("codec_name", "aac") if t_idx < len(streams) else "aac"
                    cmd += ["-map", f"0:a:{t_idx}"]
                    c_val = var_bulk_codec.get().lower() if var_bulk_codec.get() != "Copy" else "copy"
                    if c_val == "copy" and (var_bulk_bit.get() != "Original" or var_bulk_chan.get() != "Original"): c_val = raw_codec
                    cmd += [f"-c:a:{new_idx}", c_val]
                    if var_bulk_bit.get() != "Original": cmd += [f"-b:a:{new_idx}", var_bulk_bit.get()]
                    if var_bulk_chan.get() == "Stereo Downmix": cmd += [f"-ac:a:{new_idx}", "2"]
                    cmd += [f"-metadata:s:a:{new_idx}", f"language={target_lang_code}"]
                    if title_val: cmd += [f"-metadata:s:a:{new_idx}", f"title={title_val}"]
                    if clear_handler: cmd += [f"-metadata:s:a:{new_idx}", "handler_name="]

            cmd += ["-ignore_unknown", "-dn", "-write_tmcd", "0", out_file, "-y", "-loglevel", "error"]

            try:
                cflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                subprocess.run(cmd, check=True, creationflags=cflags)
                shutil.copystat(filepath, out_file)
                if do_backup: os.rename(filepath, f"{filepath}.orig")
                else: os.remove(filepath)
                os.rename(out_file, filepath)
                successful_files.append(f"[{desc}] {filepath}")
            except Exception as e:
                print(f"Error bulk processing {filepath}: {e}")
                if os.path.exists(out_file): os.remove(out_file)
                
            app.after(0, lambda p=(i+1)/total: bulk_prog_bar.configure(value=p))
            
        app.after(0, lambda: btn_bulk_go.configure(state="normal"))
        app.after(0, lambda: lbl_bulk_status.configure(text=texts.get("status_bulk_done", "Done!").replace("{count}", str(len(successful_files))), foreground="#4CAF50"))
        app.after(0, lambda: show_summary_popup(successful_files))

    threading.Thread(target=task, daemon=True).start()

def show_summary_popup(successful_files):
    sum_win = tk.Toplevel(app)
    sum_win.title(texts.get("win_summary_title", "Processing Complete"))
    sum_win.geometry("800x550")
    sum_win.grab_set()
    
    ttk.Label(sum_win, text=texts.get("lbl_summary_intro", "Successfully processed:"), font=("Segoe UI", 16, "bold")).pack(pady=10)
    txt = tk.Text(sum_win, width=90, height=20, font=("Consolas", 10), bg="#252525", fg="#FFFFFF", relief="flat")
    txt.pack(padx=10, pady=10)
    for f in successful_files: txt.insert("end", f"{f}\n")
    txt.configure(state="disabled")
    
    def export_txt():
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text File", "*.txt")], initialfile="mediafixer_report.txt")
        if path:
            with open(path, "w", encoding="utf-8") as file: file.write("\n".join(successful_files))
            messagebox.showinfo("Export", "Report saved successfully!")
            
    ttk.Button(sum_win, text=texts.get("btn_summary_export", "Export as .txt"), command=export_txt).pack(pady=10)

# Build UI
top_frame = ttk.Frame(app)
top_frame.pack(fill="x", pady=10, padx=20)
v_lang_main = tk.StringVar(value=current_config["ui_language"])
lang_menu = ttk.Combobox(top_frame, values=config.available_languages, textvariable=v_lang_main, state="readonly", width=15)
lang_menu.bind("<<ComboboxSelected>>", lambda e: on_language_changed(v_lang_main.get()))
lang_menu.pack(side="right")

tabview = ttk.Notebook(app)
tabview.pack(padx=20, pady=(0, 20), fill="both", expand=True)

tab_single = ttk.Frame(tabview)
tab_bulk = ttk.Frame(tabview)
tabview.add(tab_single, text=texts.get("tab_single", "Single File"))
tabview.add(tab_bulk, text=texts.get("tab_bulk", "Bulk"))

scroll_single = ScrollableFrame(tab_single)
scroll_single.pack(fill="both", expand=True)

frame_file_ops = ttk.LabelFrame(scroll_single.scrollable_frame, text="File Selection", padding=(15, 15))
frame_file_ops.pack(fill="x", padx=30, pady=10)

frame_save_mode = ttk.Frame(frame_file_ops)
frame_save_mode.pack(pady=5)
var_save_mode = tk.StringVar(value="inline")
ttk.Radiobutton(frame_save_mode, text=texts.get("mode_inline", "Overwrite"), variable=var_save_mode, value="inline").pack(side="left", padx=15)
ttk.Radiobutton(frame_save_mode, text=texts.get("mode_newfile", "Save As"), variable=var_save_mode, value="newfile").pack(side="left", padx=15)

btn_select_file = ttk.Button(frame_file_ops, text=texts.get("btn_file", "Select File"), command=select_single_file, style="Accent.TButton")
btn_select_file.pack(pady=15)

lbl_selected_file = ttk.Label(frame_file_ops, text=texts.get("lbl_no_file", "-"), font=("Segoe UI", 11, "italic"), foreground="gray")
lbl_selected_file.pack(pady=(0, 5))

frame_inspector = ttk.LabelFrame(scroll_single.scrollable_frame, text="Audio Streams", padding=(15, 10))
frame_inspector.pack(fill="both", expand=True, padx=30, pady=10)

header_frame = ttk.Frame(frame_inspector)
header_frame.pack(fill="x", pady=(5, 0))

header_cols = [
    (texts.get("col_lang", "Lang"), 12), 
    (texts.get("col_codec", "Codec"), 10), 
    (texts.get("col_bitrate", "Bitrate"), 12), 
    (texts.get("col_channels", "Ch"), 18), 
    (texts.get("col_action", "Action"), 15)
]
for col, w in header_cols:
    ttk.Label(header_frame, text=col, width=w, font=("Segoe UI", 10, "bold")).pack(side="left", padx=2)

scroll_table = ScrollableFrame(frame_inspector)
scroll_table.pack(padx=0, pady=(10, 15), fill="both", expand=True)
scroll_table.canvas.configure(height=300)

scroll_bulk = ScrollableFrame(tab_bulk)
scroll_bulk.pack(fill="both", expand=True)

frame_bulk_top = ttk.Frame(scroll_bulk.scrollable_frame)
frame_bulk_top.pack(pady=(15, 15))
btn_select_folder = ttk.Button(frame_bulk_top, text=texts.get("btn_folder", "Select Folder"), command=select_bulk_folder, style="Accent.TButton")
btn_select_folder.pack(side="left", padx=10)
lbl_bulk_folder = ttk.Label(frame_bulk_top, text="No folder selected", font=("Segoe UI", 11, "italic"), foreground="gray")
lbl_bulk_folder.pack(side="left", padx=10)

frame_filter = ttk.LabelFrame(scroll_bulk.scrollable_frame, text=texts.get("lbl_filter", "1. Filters"), padding=(15, 10))
frame_filter.pack(fill="x", padx=30, pady=10)

f_row1 = ttk.Frame(frame_filter)
f_row1.pack(fill="x", pady=(5, 5))

ttk.Label(f_row1, text=texts.get("lbl_ext", "Ext:")).pack(side="left")
var_bulk_ext = tk.StringVar(value=texts.get("opt_all_vids", "All Videos"))
ttk.Combobox(f_row1, values=[texts.get("opt_all_vids", "All Videos"), ".mp4", ".mkv"], textvariable=var_bulk_ext, state="readonly", width=12).pack(side="left", padx=10)
ttk.Label(f_row1, text=texts.get("lbl_contains", "Contains:")).pack(side="left", padx=(10,0))
var_bulk_contains = tk.StringVar(value="")
ttk.Entry(f_row1, textvariable=var_bulk_contains, width=20).pack(side="left", padx=10)
var_bulk_case = tk.BooleanVar(value=False)
ttk.Checkbutton(f_row1, text=texts.get("chk_case", "Case Sensitive"), variable=var_bulk_case).pack(side="left", padx=10)
var_bulk_sub = tk.BooleanVar(value=True)
ttk.Checkbutton(f_row1, text=texts.get("chk_sub", "Subfolders"), variable=var_bulk_sub).pack(side="right", padx=10)

frame_target = ttk.LabelFrame(scroll_bulk.scrollable_frame, text=texts.get("lbl_bulk_target", "2. Apply to? (Conditions)"), padding=(15, 10))
frame_target.pack(fill="x", padx=30, pady=10)

t_row1 = ttk.Frame(frame_target)
t_row1.pack(fill="x", pady=5)

opt_tracks = [texts.get("opt_all_audio", "All Audio"), texts.get("opt_track_0", "Track #0"), texts.get("opt_track_1", "Track #1"), texts.get("opt_track_custom", "Custom Track #")]
var_bulk_track = tk.StringVar(value=opt_tracks[0])
cb_track = ttk.Combobox(t_row1, values=opt_tracks, textvariable=var_bulk_track, state="readonly", width=20)
cb_track.bind("<<ComboboxSelected>>", on_track_sel_changed)
cb_track.pack(side="left", padx=5)
var_bulk_track_custom = tk.StringVar(value="0")
entry_bulk_track_custom = ttk.Entry(t_row1, textvariable=var_bulk_track_custom, width=5, state="disabled")
entry_bulk_track_custom.pack(side="left", padx=5)
var_bulk_skip = tk.BooleanVar(value=True)
ttk.Checkbutton(t_row1, text=texts.get("lbl_skip_correct", "Skip if correct"), variable=var_bulk_skip).pack(side="left", padx=20)

t_row2 = ttk.Frame(frame_target)
t_row2.pack(fill="x", pady=(5, 5))

var_cond_lang_en = tk.BooleanVar(value=False); ttk.Checkbutton(t_row2, text=texts.get("lbl_if_lang", "If Lang:"), variable=var_cond_lang_en).pack(side="left", padx=(5,0))
var_cond_lang_val = tk.StringVar(value=config.available_flags[0]); ttk.Combobox(t_row2, values=config.available_flags, textvariable=var_cond_lang_val, state="readonly", width=12).pack(side="left", padx=(5, 15))
var_cond_codec_en = tk.BooleanVar(value=False); ttk.Checkbutton(t_row2, text=texts.get("lbl_if_codec", "If Codec:"), variable=var_cond_codec_en).pack(side="left", padx=(5,0))
var_cond_codec_val = tk.StringVar(value=config.FILTER_CODEC_OPTIONS[0]); ttk.Combobox(t_row2, values=config.FILTER_CODEC_OPTIONS, textvariable=var_cond_codec_val, state="readonly", width=10).pack(side="left", padx=(5, 15))
var_cond_bit_en = tk.BooleanVar(value=False); ttk.Checkbutton(t_row2, text=texts.get("lbl_if_bitrate", "If Bitrate:"), variable=var_cond_bit_en).pack(side="left", padx=(5,0))
var_cond_bit_val = tk.StringVar(value=""); ttk.Entry(t_row2, textvariable=var_cond_bit_val, width=15).pack(side="left", padx=(5, 15))

frame_action = ttk.LabelFrame(scroll_bulk.scrollable_frame, text=texts.get("lbl_bulk_what", "3. What to do? (Action)"), padding=(15, 10))
frame_action.pack(fill="x", padx=30, pady=10)

a_row1 = ttk.Frame(frame_action)
a_row1.pack(fill="x", pady=5)

bulk_acts = [texts.get("btn_action_patch", "Patch"), texts.get("btn_action_add", "Add New"), texts.get("btn_action_delete", "Delete")]
var_bulk_act = tk.StringVar(value=bulk_acts[0])
ttk.Combobox(a_row1, values=bulk_acts, textvariable=var_bulk_act, state="readonly", width=15).pack(side="left", padx=2)
var_bulk_lang = tk.StringVar(value=config.available_flags[0])
ttk.Combobox(a_row1, values=config.available_flags, textvariable=var_bulk_lang, state="readonly", width=12).pack(side="left", padx=10)
var_bulk_codec = tk.StringVar(value="Copy")
ttk.Combobox(a_row1, values=config.CODEC_OPTIONS, textvariable=var_bulk_codec, state="readonly", width=8).pack(side="left", padx=2)
var_bulk_bit = tk.StringVar(value="Original")
ttk.Combobox(a_row1, values=config.BITRATE_OPTIONS, textvariable=var_bulk_bit, state="readonly", width=10).pack(side="left", padx=2)
var_bulk_chan = tk.StringVar(value="Original")
ttk.Combobox(a_row1, values=config.CHANNEL_OPTIONS, textvariable=var_bulk_chan, state="readonly", width=15).pack(side="left", padx=2)

a_row2 = ttk.Frame(frame_action)
a_row2.pack(fill="x", pady=(5, 5))

ttk.Label(a_row2, text=texts.get("lbl_set_title", "Set Title:")).pack(side="left", padx=(2, 5))
var_bulk_title = tk.StringVar(value="")
ttk.Entry(a_row2, textvariable=var_bulk_title, width=35).pack(side="left", padx=5)

var_bulk_clear_handler = tk.BooleanVar(value=False)
ttk.Checkbutton(a_row2, text=texts.get("chk_clear_handler", "Clear Handler Name"), variable=var_bulk_clear_handler).pack(side="left", padx=15)

frame_start = ttk.Frame(scroll_bulk.scrollable_frame)
frame_start.pack(fill="x", padx=30, pady=(20, 10))

options_row = ttk.Frame(frame_start)
options_row.pack(fill="x", pady=10)

var_bulk_backup = tk.BooleanVar(value=True)
ttk.Checkbutton(options_row, text=texts.get("lbl_backup", "Keep Original File as Backup (.orig)"), variable=var_bulk_backup).pack(side="left", padx=(150, 20))

ttk.Label(options_row, text=texts.get("lbl_cpu_load", "CPU Usage:")).pack(side="left", padx=(20, 5))

var_bulk_cpu = tk.StringVar(value=texts.get("opt_cpu_max", "Maximum"))
cpu_opts = [
    texts.get("opt_cpu_max", "Maximum"),
    texts.get("opt_cpu_med", "Medium"),
    texts.get("opt_cpu_low", "Low")
]
cb_cpu = ttk.Combobox(options_row, values=cpu_opts, textvariable=var_bulk_cpu, state="readonly", width=22)
cb_cpu.pack(side="left")

btn_bulk_go = ttk.Button(frame_start, text=texts.get("btn_start_bulk", "Vorschau & Simulation"), style="Accent.TButton", command=simulate_bulk_process)
btn_bulk_go.pack(pady=10, fill="x", padx=150)

bulk_prog_bar = ttk.Progressbar(frame_start, maximum=1.0, mode="determinate")
bulk_prog_bar.pack(fill="x", padx=40, pady=15)
lbl_bulk_status = ttk.Label(frame_start, text="", font=("Segoe UI", 10))
lbl_bulk_status.pack()

# Startup sequence
status_frame = ttk.Frame(app, padding=(20, 5))
status_frame.pack(side="bottom", fill="x")
lbl_status_main = ttk.Label(status_frame, text="", font=("Segoe UI", 10, "bold"))
lbl_status_main.pack(side="left")

lbl_version = ttk.Label(status_frame, text=f"v{config.APP_VERSION}", font=("Segoe UI", 10), foreground="gray")
lbl_version.pack(side="right")

system_ready = update_main_status()

if not os.path.exists(config.CONFIG_FILE) or not system_ready:
    app.after(100, show_setup_wizard)

threading.Thread(target=check_for_updates, daemon=True).start()

# Global OS-specific mousewheel handler
def on_mousewheel(event):
    # Determine direction based on OS
    if platform.system() == "Windows":
        direction = int(-1*(event.delta/120))
    elif platform.system() == "Darwin":
        direction = int(-1*event.delta)
    else:
        direction = -1 if event.num == 4 else 1

    widget = app.winfo_containing(event.x_root, event.y_root)
    
    # Prevent accidental value changes when hovering over comboboxes
    if widget and widget.winfo_class() == "TCombobox":
        return
        
    # Traverse up to find the nearest scrollable canvas
    while widget:
        if widget.winfo_class() == "Canvas" and widget.cget("yscrollcommand"):
            widget.yview_scroll(direction, "units")
            return
        widget = widget.master

# Bind globally
if platform.system() == "Linux":
    app.bind_all("<Button-4>", on_mousewheel)
    app.bind_all("<Button-5>", on_mousewheel)
else:
    app.bind_all("<MouseWheel>", on_mousewheel)

app.mainloop()