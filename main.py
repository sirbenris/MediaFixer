import customtkinter
from customtkinter import filedialog
import tkinter.messagebox as messagebox
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

# Import separated modules
import config
from config import current_config, texts, audio_flags as AUDIO_FLAGS
import media_engine

# --- UI Initialization ---
customtkinter.set_appearance_mode("dark")

# Loads custom theme JSON instead of standard colors.
customtkinter.set_default_color_theme(config.resource_path("rime.json"))

app = customtkinter.CTk()
app.geometry("1100x900")

# --- Global Variables for Linter & State ---
lbl_status_main = None
btn_select_file = None
btn_select_folder = None
lbl_selected_file = None
scroll_table = None
header_frame = None
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


# --- Helper Functions ---
def check_for_updates():
    # Wir überspringen den Check, wenn du lokal in der "dev" Umgebung bist
    if config.APP_VERSION == "dev":
        return

    try:
        url = "https://api.github.com/repos/sirbenris/MediaFixer/releases/latest"
        req = urllib.request.Request(url, headers={'User-Agent': 'MediaFixer-Update-Check'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            latest_version = data.get("tag_name", "").replace("v", "")
            
            # Einfache Stringprüfung
            if latest_version and latest_version != config.APP_VERSION:
                app.after(1500, lambda v=latest_version: show_update_popup(v))
    except Exception as e:
        print(f"Update check failed: {e}")

def show_update_popup(new_version):
    msg = texts.get("update_msg", f"A new version ({new_version}) is available!\nDo you want to download it?").replace("{v}", new_version)
    if messagebox.askyesno(texts.get("update_title", "Update available!"), msg):
        webbrowser.open("https://github.com/sirbenris/MediaFixer/releases/latest")

def update_main_status():
    if not all([lbl_status_main, btn_select_file, btn_select_folder]): 
        return False
        
    if media_engine.check_ffmpeg_installed():
        lbl_status_main.configure(text=texts.get("status_ready", "✅ FFmpeg Ready"), text_color="green")
        btn_select_file.configure(state="normal")
        btn_select_folder.configure(state="normal")
        return True
        
    lbl_status_main.configure(text=texts.get("status_missing", "❌ FFmpeg Missing!"), text_color="red")
    btn_select_file.configure(state="disabled")
    btn_select_folder.configure(state="disabled")
    return False

def on_language_changed(choice):
    if choice == current_config["ui_language"]: 
        return
    current_config["ui_language"] = choice
    config.save_config()
    app.destroy()
    os.execl(sys.executable, sys.executable, *sys.argv)

def show_setup_wizard():
    wizard = customtkinter.CTkToplevel(app)
    wizard.title("Media Fixer - Setup")
    wizard.geometry("600x500")
    wizard.attributes("-topmost", True)
    wizard.grab_set()
    
    customtkinter.CTkLabel(wizard, text="System-Check:", font=("Arial", 16, "bold")).pack(pady=15)
    lbl_status = customtkinter.CTkLabel(wizard, text="Checking FFmpeg...")
    lbl_status.pack(pady=5)
    
    is_installed = media_engine.check_ffmpeg_installed()
    btn_save = customtkinter.CTkButton(wizard, text="Finish & Start", font=("Arial", 14, "bold"), state="disabled")

    def run_download():
        def task():
            success = media_engine.download_ffmpeg_windows(lambda msg: lbl_status.configure(text=msg))
            if success:
                lbl_status.configure(text="✅ FFmpeg installed successfully!", text_color="green")
                btn_save.configure(state="normal")
                update_main_status()
            else:
                lbl_status.configure(text="❌ Download failed!", text_color="red")
        threading.Thread(target=task, daemon=True).start()

    if is_installed:
        lbl_status.configure(text="✅ FFmpeg found!", text_color="green")
        btn_save.configure(state="normal")
    else:
        if platform.system() == "Windows":
            lbl_status.configure(text="❌ FFmpeg missing on your system.", text_color="red")
            btn_dl = customtkinter.CTkButton(wizard, text="📥 Download FFmpeg (Portable)", command=run_download)
            btn_dl.pack(pady=10)
        else:
            cmd_hint = "sudo apt install ffmpeg" if platform.system() == "Linux" else "brew install ffmpeg"
            lbl_status.configure(text=f"❌ FFmpeg missing!\n\nPlease install it via terminal:\n{cmd_hint}", text_color="orange")
            btn_recheck = customtkinter.CTkButton(wizard, text="🔄 Re-Check", command=lambda: btn_save.configure(state="normal") if media_engine.check_ffmpeg_installed() else None)
            btn_recheck.pack(pady=10)
        
    customtkinter.CTkLabel(wizard, text="Default UI Language:").pack(pady=(20, 5))
    var_ui = customtkinter.StringVar(value=config.available_languages[0])
    customtkinter.CTkOptionMenu(wizard, values=config.available_languages, variable=var_ui).pack()
    
    def on_save_wizard():
        current_config["ui_language"] = var_ui.get()
        config.save_config()
        wizard.destroy()
        
    btn_save.configure(command=on_save_wizard)
    btn_save.pack(pady=30)

# --- Single File Processing ---
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

        if action == "Delete":
            cmd += ["-map", f"-0:a:{a_idx}"]
        elif action == "Patch":
            c_val = codec.lower() if codec != "Copy" else "copy"
            
            # --- SMART FALLBACK ---
            # Wenn Copy gewählt ist, wir aber Bitrate/Kanäle ändern wollen, MÜSSEN wir re-encodieren. 
            # Wir nutzen dafür den Ursprungs-Codec der Spur.
            if c_val == "copy" and (bitrate != "Original" or channels != "Original"):
                c_val = raw_codec
                
            cmd += [f"-c:a:{a_idx}", c_val]
            if bitrate != "Original": cmd += [f"-b:a:{a_idx}", bitrate]
            if channels == "Stereo Downmix": cmd += [f"-ac:a:{a_idx}", "2"]
            cmd += [f"-metadata:s:a:{a_idx}", f"language={lang}"]
            cmd += [f"-metadata:s:a:{a_idx}", f"title={title_val}"]
            if clear_handler: cmd += [f"-metadata:s:a:{a_idx}", "handler_name="]
            
        elif action == "Add New":
            cmd += ["-map", f"0:a:{a_idx}"]
            c_val = codec.lower() if codec != "Copy" else "copy"
            
            # --- SMART FALLBACK ---
            if c_val == "copy" and (bitrate != "Original" or channels != "Original"):
                c_val = raw_codec
                
            cmd += [f"-c:a:{total}", c_val]
            if bitrate != "Original": cmd += [f"-b:a:{total}", bitrate]
            if channels == "Stereo Downmix": cmd += [f"-ac:a:{total}", "2"]
            cmd += [f"-metadata:s:a:{total}", f"language={lang}"]
            cmd += [f"-metadata:s:a:{total}", f"title={title_val}"]
            if clear_handler: cmd += [f"-metadata:s:a:{total}", "handler_name="]

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
                    app.after(0, lambda p=pct: (p_b.set(p), p_l.configure(text=f"{int(p*100)}%")))
            process.wait()
            if process.returncode == 0:
                shutil.copystat(orig_path, out_file)
                if mode == "inline":
                    os.remove(orig_path)
                    os.rename(out_file, orig_path)
                app.after(0, lambda: btn.configure(text=texts.get("status_success", "✅ Done!"), fg_color="green"))
                app.after(1000, analyze_file, orig_path if mode == "inline" else target_path)
            else: raise Exception("FFmpeg error")
        except Exception as e:
            app.after(0, lambda: btn.configure(text=texts.get("status_failed", "❌ Error!"), fg_color="red", state="normal"))
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
    for widget in scroll_table.winfo_children(): widget.destroy()
    lbl_selected_file.configure(text=texts.get("lbl_analyzing", "Analyzing..."), text_color="yellow")
    app.update()
    
    data = media_engine.probe_file(filepath)
    if not data:
        customtkinter.CTkLabel(scroll_table, text=texts.get("lbl_no_audio", "No Audio found.")).pack(pady=20)
        lbl_selected_file.configure(text=os.path.basename(filepath), text_color="white")
        return
        
    streams = data.get("streams", [])
    duration = float(data.get("format", {}).get("duration", 1.0))
    lbl_selected_file.configure(text=os.path.basename(filepath), text_color="white")
    act_map = {texts.get("btn_action_patch", "Patch"): "Patch", texts.get("btn_action_add", "Add New"): "Add New", texts.get("btn_action_delete", "Delete"): "Delete"}

    for a_idx, stream in enumerate(streams):
        tags = stream.get("tags", {})
        lang_orig = tags.get("language", "und")
        codec_orig = stream.get("codec_name", "unk").upper()
        # Den echten FFmpeg Codec-Namen (z.B. 'aac', 'ac3') für den Fallback speichern
        raw_codec = stream.get("codec_name", "aac") 
        channels_orig = stream.get("channels", "?")
        bps = stream.get("bit_rate") or tags.get("BPS")
        bitrate_kbps = f"{int(bps)//1000} kbps" if str(bps).isdigit() else texts.get("unknown_bitrate", "???")
        track_title = tags.get("title", "")
        title_display = f" - '{track_title}'" if track_title else ""
        
        row = customtkinter.CTkFrame(scroll_table, fg_color=("gray80", "gray20"))
        row.pack(fill="x", pady=5, padx=5)

        info_text = f"🎵 #{a_idx} | [{lang_orig}] | {codec_orig} | {bitrate_kbps} | {channels_orig} Ch{title_display}"
        customtkinter.CTkLabel(row, text=info_text, font=("Arial", 11, "bold"), text_color="gray70").pack(side="top", anchor="w", padx=10, pady=2)
        
        ctrl = customtkinter.CTkFrame(row, fg_color="transparent")
        ctrl.pack(side="top", fill="x", padx=5, pady=2)

        v_lang = customtkinter.StringVar(value=[k for k,v in AUDIO_FLAGS.items() if v == lang_orig][0] if lang_orig in AUDIO_FLAGS.values() else "English")
        customtkinter.CTkOptionMenu(ctrl, values=config.available_flags, variable=v_lang, width=110).pack(side="left", padx=2)
        v_codec = customtkinter.StringVar(value="Copy")
        customtkinter.CTkOptionMenu(ctrl, values=config.CODEC_OPTIONS, variable=v_codec, width=85, fg_color="gray30").pack(side="left", padx=2)
        v_bit = customtkinter.StringVar(value="Original")
        customtkinter.CTkOptionMenu(ctrl, values=config.BITRATE_OPTIONS, variable=v_bit, width=100, fg_color="gray30").pack(side="left", padx=2)
        v_chan = customtkinter.StringVar(value="Original")
        customtkinter.CTkOptionMenu(ctrl, values=config.CHANNEL_OPTIONS, variable=v_chan, width=130, fg_color="gray30").pack(side="left", padx=2)
        v_act = customtkinter.StringVar(value=list(act_map.keys())[0])
        customtkinter.CTkOptionMenu(ctrl, values=list(act_map.keys()), variable=v_act, width=130, button_color="darkblue").pack(side="left", padx=2)

        ctrl2 = customtkinter.CTkFrame(row, fg_color="transparent")
        ctrl2.pack(side="top", fill="x", padx=5, pady=(0, 5))
        
        customtkinter.CTkLabel(ctrl2, text=texts.get("lbl_title", "Title:")).pack(side="left", padx=(2, 5))
        v_title = customtkinter.StringVar(value=track_title)
        customtkinter.CTkEntry(ctrl2, textvariable=v_title, width=220).pack(side="left", padx=2)
        
        v_clear = customtkinter.BooleanVar(value=False)
        customtkinter.CTkCheckBox(ctrl2, text=texts.get("chk_clear_handler", "Clear Handler Name"), variable=v_clear).pack(side="left", padx=15)

        p_f = customtkinter.CTkFrame(row, fg_color="transparent")
        p_b = customtkinter.CTkProgressBar(p_f, height=8); p_b.pack(side="left", fill="x", expand=True, padx=(0, 10)); p_b.set(0)
        p_l = customtkinter.CTkLabel(p_f, text="0%", font=("Arial", 10, "bold")); p_l.pack(side="right")

        # Hier wird der 'raw_codec' heimlich an den Button übergeben
        btn_go = customtkinter.CTkButton(ctrl, text="GO", width=50, font=("Arial", 12, "bold"), fg_color="#1f538d")
        btn_go.configure(command=lambda a=a_idx, l=v_lang, c=v_codec, b=v_bit, ch=v_chan, act=v_act, tit=v_title, clr=v_clear, rc=raw_codec, btn=btn_go, p_f=p_f, p_b=p_b, p_l=p_l: 
            threading.Thread(target=lambda: on_go_clicked(filepath, a, l, c, b, ch, act, tit, clr, rc, btn, len(streams), duration, p_f, p_b, p_l)).start()
        )
        btn_go.pack(side="right", padx=5)

# --- Bulk Processing ---
def select_bulk_folder():
    global bulk_target_folder
    folder = filedialog.askdirectory(title=texts.get("btn_folder", "Select Folder"))
    if folder:
        bulk_target_folder = folder
        lbl_bulk_folder.configure(text=folder, text_color="white")

def on_track_sel_changed(choice):
    if choice == texts.get("opt_track_custom", "Custom Track #"): entry_bulk_track_custom.configure(state="normal")
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
        # Check Conditions
        if var_cond_lang_en.get() and tags.get("language", "und") != AUDIO_FLAGS.get(var_cond_lang_val.get(), "und"): continue
        if var_cond_codec_en.get() and stream.get("codec_name", "unk").upper() != var_cond_codec_val.get(): continue
        if var_cond_bit_en.get():
            bps = stream.get("bit_rate") or tags.get("BPS")
            kbps = str(int(bps)//1000) if str(bps).isdigit() else ""
            target_bps = var_cond_bit_val.get().strip()
            if target_bps and target_bps != kbps: continue

        # Smart Skip Logic: Only skip if ALL requested changes are already present!
        if var_bulk_skip.get() and var_bulk_act.get() == texts.get("btn_action_patch", "Patch"):
            already_lang = tags.get("language", "und") == AUDIO_FLAGS.get(var_bulk_lang.get(), "und")
            already_codec = (var_bulk_codec.get() == "Copy") or (stream.get("codec_name", "unk").upper() == var_bulk_codec.get().upper())
            already_title = (not var_bulk_title.get()) or (tags.get("title", "") == var_bulk_title.get())
            already_handler = (not var_bulk_clear_handler.get()) or ("handler_name" not in tags)
            
            # If everything is already as the user wants it, skip this stream
            if already_lang and already_codec and already_title and already_handler:
                continue

        matched.append(a_idx)
    
    return matched, len(streams)

def simulate_bulk_process():
    if not bulk_target_folder: 
        messagebox.showwarning(texts.get("warn_title", "Warning"), texts.get("warn_no_folder", "Please select a folder first!"))
        return
        
    # --- NEU: Warnung, falls "Alle Audiostreams" ausgewählt ist ---
    if var_bulk_track.get() == texts.get("opt_all_audio", "All Audio Streams"):
        confirm_all = messagebox.askyesno(
            texts.get("warn_title", "Warning"), 
            texts.get("warn_all_audio", "You selected 'All Audio Streams'. This will modify EVERY matching track. Proceed?")
        )
        if not confirm_all: 
            return
    
    # Check für Backup-Warnung
    do_backup = bool(var_bulk_backup.get())
    if not do_backup:
        confirm_backup = messagebox.askyesno(texts.get("warn_title", "Warning"), texts.get("warn_msg", "Proceed without backups?"))
        if not confirm_backup: return

    def task():
        app.after(0, lambda: btn_bulk_go.configure(state="disabled"))
        app.after(0, lambda: lbl_bulk_status.configure(text=texts.get("status_bulk_scan", "Scanning..."), text_color="yellow"))
        
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
            app.after(0, lambda: lbl_bulk_status.configure(text=texts.get("status_bulk_empty", "Empty"), text_color="orange"))
            app.after(0, lambda: btn_bulk_go.configure(state="normal"))
            return

        app.after(0, lambda: bulk_prog_bar.set(0))
        total_files = len(filtered_files)
        planned_changes = []

        for i, filepath in enumerate(filtered_files):
            matched_indices, total_audio = match_bulk_streams(filepath)
            if matched_indices:
                # Format exactly what tracks are affected (e.g. "0, 1")
                tracks_str = ", ".join(str(idx) for idx in matched_indices)
                
                if action == texts.get("btn_action_delete", "Delete"):
                    desc = f"Delete Track(s) #{tracks_str}"
                else:
                    act_word = "Patch" if action == texts.get("btn_action_patch", "Patch") else "Add"
                    # Build dynamic description based on user inputs
                    desc_parts = [f"{act_word} #{tracks_str} -> [{target_lang_code}]"]
                    if codec_val != "Copy": desc_parts.append(f"Codec: {codec_val}")
                    if title_val: desc_parts.append(f"Title: '{title_val}'")
                    if clear_handler: desc_parts.append("Clear Handler")
                        
                    desc = " | ".join(desc_parts)

                planned_changes.append({"filepath": filepath, "desc": desc, "matched_indices": matched_indices, "total_audio": total_audio})
                
            app.after(0, lambda p=(i+1)/total_files: bulk_prog_bar.set(p))

        app.after(0, lambda: show_simulation_popup(planned_changes))
        app.after(0, lambda: lbl_bulk_status.configure(text="Scan complete.", text_color="white"))
        app.after(0, lambda: btn_bulk_go.configure(state="normal"))

    threading.Thread(target=task, daemon=True).start()

def show_simulation_popup(planned_changes):
    if not planned_changes:
        messagebox.showinfo("Info", texts.get("status_bulk_empty", "Empty"))
        return
        
    sim_win = customtkinter.CTkToplevel(app)
    sim_win.title(texts.get("win_sim_title", "Simulation"))
    sim_win.geometry("800x550")
    sim_win.grab_set()
    
    customtkinter.CTkLabel(sim_win, text=texts.get("lbl_sim_intro", "Planned changes:"), font=("Arial", 16, "bold")).pack(pady=10)
    txt = customtkinter.CTkTextbox(sim_win, width=750, height=400, font=("Courier", 12))
    txt.pack(padx=10, pady=10)
    for chg in planned_changes: txt.insert("end", f"[{chg['desc']}]  ->  {os.path.basename(chg['filepath'])}\n")
    txt.configure(state="disabled")
    
    btn_frame = customtkinter.CTkFrame(sim_win, fg_color="transparent")
    btn_frame.pack(pady=10)
    
    customtkinter.CTkButton(btn_frame, text=texts.get("btn_sim_cancel", "Cancel"), command=sim_win.destroy, fg_color="gray").pack(side="left", padx=10)
    customtkinter.CTkButton(btn_frame, text=texts.get("btn_sim_execute", "Execute Now!"), fg_color="darkred", hover_color="#8b0000", command=lambda: execute_bulk_process(planned_changes, sim_win)).pack(side="left", padx=10)

def execute_bulk_process(planned_changes, sim_win):
    sim_win.destroy()
    do_backup = bool(var_bulk_backup.get())
    
    def task():
        app.after(0, lambda: btn_bulk_go.configure(state="disabled"))
        app.after(0, lambda: bulk_prog_bar.set(0))
        
        total = len(planned_changes)
        successful_files = []
        
        for i, chg in enumerate(planned_changes):
            filepath = chg['filepath']
            desc = chg['desc']
            matched_indices = chg['matched_indices']
            total_audio = chg['total_audio']
            
            app.after(0, lambda d=desc, f=os.path.basename(filepath): lbl_bulk_status.configure(text=f"{d} : {f}"))
            
            # Kurz neu scannen, um die Original-Codecs für den Smart Fallback parat zu haben
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
                    
                    # --- SMART FALLBACK ---
                    if c_val == "copy" and (var_bulk_bit.get() != "Original" or var_bulk_chan.get() != "Original"):
                        c_val = raw_codec
                        
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
                    
                    # --- SMART FALLBACK ---
                    if c_val == "copy" and (var_bulk_bit.get() != "Original" or var_bulk_chan.get() != "Original"):
                        c_val = raw_codec
                        
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
                
            app.after(0, lambda p=(i+1)/total: bulk_prog_bar.set(p))
            
        app.after(0, lambda: btn_bulk_go.configure(state="normal"))
        app.after(0, lambda: lbl_bulk_status.configure(text=texts.get("status_bulk_done", "Done!").replace("{count}", str(len(successful_files))), text_color="green"))
        app.after(0, lambda: show_summary_popup(successful_files))

    threading.Thread(target=task, daemon=True).start()

def show_summary_popup(successful_files):
    sum_win = customtkinter.CTkToplevel(app)
    sum_win.title(texts.get("win_summary_title", "Processing Complete"))
    sum_win.geometry("800x550")
    sum_win.grab_set()
    
    customtkinter.CTkLabel(sum_win, text=texts.get("lbl_summary_intro", "Successfully processed:"), font=("Arial", 16, "bold")).pack(pady=10)
    txt = customtkinter.CTkTextbox(sum_win, width=750, height=400, font=("Courier", 11))
    txt.pack(padx=10, pady=10)
    for f in successful_files: txt.insert("end", f"{f}\n")
    txt.configure(state="disabled")
    
    def export_txt():
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text File", "*.txt")], initialfile="mediafixer_report.txt")
        if path:
            with open(path, "w", encoding="utf-8") as file: file.write("\n".join(successful_files))
            messagebox.showinfo("Export", "Report saved successfully!")
            
    customtkinter.CTkButton(sum_win, text=texts.get("btn_summary_export", "Export as .txt"), command=export_txt).pack(pady=10)


# ==========================================
# --- UI CONSTRUCTION ---
# ==========================================

app.title(texts.get("app_title", "Media Fixer"))

lang_menu = customtkinter.CTkOptionMenu(app, values=config.available_languages, command=on_language_changed)
lang_menu.set(current_config["ui_language"])
lang_menu.pack(pady=10, padx=20, anchor="e")

tabview = customtkinter.CTkTabview(app)
tabview.pack(padx=20, pady=0, fill="both", expand=True)

tab_single = tabview.add(texts.get("tab_single", "Single File"))
tab_bulk = tabview.add(texts.get("tab_bulk", "Bulk"))

# ==========================================
# --- Tab 1: Single File Processing ---
# ==========================================

# Main scrollable container for the single file tab
scroll_single = customtkinter.CTkScrollableFrame(tab_single, fg_color="transparent")
scroll_single.pack(fill="both", expand=True, padx=0, pady=0)

customtkinter.CTkLabel(scroll_single, text=texts.get("lbl_single", "Inspector"), font=("Arial", 22, "bold")).pack(pady=(10, 20))

# --- Section 1: File Selection & Save Mode ---
# Card for file selection and output configuration
frame_file_ops = customtkinter.CTkFrame(scroll_single, corner_radius=10, border_width=1)
frame_file_ops.pack(fill="x", padx=30, pady=10)

customtkinter.CTkLabel(frame_file_ops, text="File Selection", font=("Arial", 16, "bold"), text_color="#3a7ebf").pack(anchor="w", padx=15, pady=(15, 5))

# Save mode radio buttons
frame_save_mode = customtkinter.CTkFrame(frame_file_ops, fg_color="transparent")
frame_save_mode.pack(pady=5)
var_save_mode = customtkinter.StringVar(value="inline")
customtkinter.CTkRadioButton(frame_save_mode, text=texts.get("mode_inline", "Overwrite"), variable=var_save_mode, value="inline").pack(side="left", padx=15)
customtkinter.CTkRadioButton(frame_save_mode, text=texts.get("mode_newfile", "Save As"), variable=var_save_mode, value="newfile").pack(side="left", padx=15)

# Selection button and file path display
btn_select_file = customtkinter.CTkButton(frame_file_ops, text=texts.get("btn_file", "Select File"), font=("Arial", 14, "bold"), command=select_single_file)
btn_select_file.pack(pady=15)

lbl_selected_file = customtkinter.CTkLabel(frame_file_ops, text=texts.get("lbl_no_file", "-"), font=("Arial", 13, "italic"), text_color="gray")
lbl_selected_file.pack(pady=(0, 15))

# --- Section 2: Audio Stream Inspector ---
# Card for displaying analyzed audio tracks
frame_inspector = customtkinter.CTkFrame(scroll_single, corner_radius=10, border_width=1)
frame_inspector.pack(fill="both", expand=True, padx=30, pady=10)

customtkinter.CTkLabel(frame_inspector, text="Audio Streams", font=("Arial", 16, "bold"), text_color="#3a7ebf").pack(anchor="w", padx=15, pady=(15, 5))

# Table header for stream information
header_frame = customtkinter.CTkFrame(frame_inspector, fg_color="transparent")
header_frame.pack(fill="x", padx=15, pady=(5, 0))

# Define column headers based on current configuration
header_cols = [
    (texts.get("col_lang", "Lang"), 110), 
    (texts.get("col_codec", "Codec"), 85), 
    (texts.get("col_bitrate", "Bitrate"), 100), 
    (texts.get("col_channels", "Ch"), 130), 
    (texts.get("col_action", "Action"), 130)
]

for col, w in header_cols:
    customtkinter.CTkLabel(header_frame, text=col, width=w, anchor="w", font=("Arial", 12, "bold")).pack(side="left", padx=2)

# Dynamic list of audio tracks
scroll_table = customtkinter.CTkScrollableFrame(frame_inspector, fg_color="transparent", height=400)
scroll_table.pack(padx=10, pady=(5, 15), fill="both", expand=True)

# ==========================================
# --- Tab 2: Bulk Processing ---
# ==========================================

# Main scrollable container for the bulk tab to prevent UI overflow
scroll_bulk = customtkinter.CTkScrollableFrame(tab_bulk, fg_color="transparent")
scroll_bulk.pack(fill="both", expand=True, padx=0, pady=0)

customtkinter.CTkLabel(scroll_bulk, text=texts.get("lbl_bulk", "Bulk Processing"), font=("Arial", 22, "bold")).pack(pady=(10, 20))

frame_bulk_top = customtkinter.CTkFrame(scroll_bulk, fg_color="transparent")
frame_bulk_top.pack(pady=(0, 15))
btn_select_folder = customtkinter.CTkButton(frame_bulk_top, text=texts.get("btn_folder", "Select Folder"), font=("Arial", 14, "bold"), height=35, command=select_bulk_folder)
btn_select_folder.pack(side="left", padx=10)
lbl_bulk_folder = customtkinter.CTkLabel(frame_bulk_top, text="No folder selected", font=("Arial", 13, "italic"), text_color="gray50")
lbl_bulk_folder.pack(side="left", padx=10)

# --- Section 1: Filters ---
# Container configured as a card with border and contrasting background.
frame_filter = customtkinter.CTkFrame(scroll_bulk, corner_radius=10, fg_color=("gray85", "gray16"), border_width=1, border_color=("gray75", "gray25"))
frame_filter.pack(fill="x", padx=30, pady=10)
customtkinter.CTkLabel(frame_filter, text=texts.get("lbl_filter", "1. Filters"), font=("Arial", 16, "bold"), text_color="#3a7ebf").pack(anchor="w", padx=15, pady=(15, 5))

f_row1 = customtkinter.CTkFrame(frame_filter, fg_color="transparent")
f_row1.pack(fill="x", padx=15, pady=(5, 15))

# Filter inputs initialization
customtkinter.CTkLabel(f_row1, text=texts.get("lbl_ext", "Ext:")).pack(side="left")
var_bulk_ext = customtkinter.StringVar(value=texts.get("opt_all_vids", "All Videos"))
customtkinter.CTkOptionMenu(f_row1, values=[texts.get("opt_all_vids", "All Videos"), ".mp4", ".mkv"], variable=var_bulk_ext, width=120).pack(side="left", padx=10)
customtkinter.CTkLabel(f_row1, text=texts.get("lbl_contains", "Contains:")).pack(side="left", padx=(10,0))
var_bulk_contains = customtkinter.StringVar(value="")
customtkinter.CTkEntry(f_row1, textvariable=var_bulk_contains, width=150).pack(side="left", padx=10)
var_bulk_case = customtkinter.BooleanVar(value=False)
customtkinter.CTkCheckBox(f_row1, text=texts.get("chk_case", "Case Sensitive"), variable=var_bulk_case).pack(side="left", padx=10)
var_bulk_sub = customtkinter.BooleanVar(value=True)
customtkinter.CTkCheckBox(f_row1, text=texts.get("chk_sub", "Subfolders"), variable=var_bulk_sub).pack(side="right", padx=10)

# --- Section 2: Conditions ---
frame_target = customtkinter.CTkFrame(scroll_bulk, corner_radius=10, fg_color=("gray85", "gray16"), border_width=1, border_color=("gray75", "gray25"))
frame_target.pack(fill="x", padx=30, pady=10)
customtkinter.CTkLabel(frame_target, text=texts.get("lbl_bulk_target", "2. Apply to? (Conditions)"), font=("Arial", 16, "bold"), text_color="#3a7ebf").pack(anchor="w", padx=15, pady=(15, 5))

t_row1 = customtkinter.CTkFrame(frame_target, fg_color="transparent")
t_row1.pack(fill="x", padx=15, pady=5)

# Track selection inputs
opt_tracks = [texts.get("opt_all_audio", "All Audio"), texts.get("opt_track_0", "Track #0"), texts.get("opt_track_1", "Track #1"), texts.get("opt_track_custom", "Custom Track #")]
var_bulk_track = customtkinter.StringVar(value=opt_tracks[0])
customtkinter.CTkOptionMenu(t_row1, values=opt_tracks, variable=var_bulk_track, width=160, command=on_track_sel_changed).pack(side="left", padx=5)
var_bulk_track_custom = customtkinter.StringVar(value="0")
entry_bulk_track_custom = customtkinter.CTkEntry(t_row1, textvariable=var_bulk_track_custom, width=50, state="disabled")
entry_bulk_track_custom.pack(side="left", padx=5)
var_bulk_skip = customtkinter.BooleanVar(value=True)
customtkinter.CTkCheckBox(t_row1, text=texts.get("lbl_skip_correct", "Skip if correct"), variable=var_bulk_skip).pack(side="left", padx=20)

t_row2 = customtkinter.CTkFrame(frame_target, fg_color="transparent")
t_row2.pack(fill="x", padx=15, pady=(5, 15))

# Conditional processing parameters
var_cond_lang_en = customtkinter.BooleanVar(value=False); customtkinter.CTkCheckBox(t_row2, text=texts.get("lbl_if_lang", "If Lang:"), variable=var_cond_lang_en, width=80).pack(side="left", padx=(5,0))
var_cond_lang_val = customtkinter.StringVar(value=config.available_flags[0]); customtkinter.CTkOptionMenu(t_row2, values=config.available_flags, variable=var_cond_lang_val, width=100).pack(side="left", padx=(5, 15))
var_cond_codec_en = customtkinter.BooleanVar(value=False); customtkinter.CTkCheckBox(t_row2, text=texts.get("lbl_if_codec", "If Codec:"), variable=var_cond_codec_en, width=80).pack(side="left", padx=(5,0))
var_cond_codec_val = customtkinter.StringVar(value=config.FILTER_CODEC_OPTIONS[0]); customtkinter.CTkOptionMenu(t_row2, values=config.FILTER_CODEC_OPTIONS, variable=var_cond_codec_val, width=85).pack(side="left", padx=(5, 15))
var_cond_bit_en = customtkinter.BooleanVar(value=False); customtkinter.CTkCheckBox(t_row2, text=texts.get("lbl_if_bitrate", "If Bitrate:"), variable=var_cond_bit_en, width=80).pack(side="left", padx=(5,0))
var_cond_bit_val = customtkinter.StringVar(value=""); customtkinter.CTkEntry(t_row2, textvariable=var_cond_bit_val, width=100, placeholder_text="kbps (e.g. 192)").pack(side="left", padx=(5, 15))

# --- Section 3: Action ---
frame_action = customtkinter.CTkFrame(scroll_bulk, corner_radius=10, fg_color=("gray85", "gray16"), border_width=1, border_color=("gray75", "gray25"))
frame_action.pack(fill="x", padx=30, pady=10)
customtkinter.CTkLabel(frame_action, text=texts.get("lbl_bulk_what", "3. What to do? (Action)"), font=("Arial", 16, "bold"), text_color="#3a7ebf").pack(anchor="w", padx=15, pady=(15, 5))

a_row1 = customtkinter.CTkFrame(frame_action, fg_color="transparent")
a_row1.pack(fill="x", padx=15, pady=5)

# Processing action parameters
bulk_acts = [texts.get("btn_action_patch", "Patch"), texts.get("btn_action_add", "Add New"), texts.get("btn_action_delete", "Delete")]
var_bulk_act = customtkinter.StringVar(value=bulk_acts[0])
customtkinter.CTkOptionMenu(a_row1, values=bulk_acts, variable=var_bulk_act, width=130, button_color="darkblue").pack(side="left", padx=2)
var_bulk_lang = customtkinter.StringVar(value=config.available_flags[0])
customtkinter.CTkOptionMenu(a_row1, values=config.available_flags, variable=var_bulk_lang, width=110).pack(side="left", padx=10)
var_bulk_codec = customtkinter.StringVar(value="Copy")
customtkinter.CTkOptionMenu(a_row1, values=config.CODEC_OPTIONS, variable=var_bulk_codec, width=85, fg_color="gray30").pack(side="left", padx=2)
var_bulk_bit = customtkinter.StringVar(value="Original")
customtkinter.CTkOptionMenu(a_row1, values=config.BITRATE_OPTIONS, variable=var_bulk_bit, width=100, fg_color="gray30").pack(side="left", padx=2)
var_bulk_chan = customtkinter.StringVar(value="Original")
customtkinter.CTkOptionMenu(a_row1, values=config.CHANNEL_OPTIONS, variable=var_bulk_chan, width=130, fg_color="gray30").pack(side="left", padx=2)

a_row2 = customtkinter.CTkFrame(frame_action, fg_color="transparent")
a_row2.pack(fill="x", padx=15, pady=(5, 15))

customtkinter.CTkLabel(a_row2, text=texts.get("lbl_set_title", "Set Title (Leave empty to keep original):")).pack(side="left", padx=(2, 5))
var_bulk_title = customtkinter.StringVar(value="")
customtkinter.CTkEntry(a_row2, textvariable=var_bulk_title, width=250, placeholder_text=texts.get("plc_keep_title", "Leave empty to keep original")).pack(side="left", padx=5)

var_bulk_clear_handler = customtkinter.BooleanVar(value=False)
customtkinter.CTkCheckBox(a_row2, text=texts.get("chk_clear_handler", "Clear Handler Name"), variable=var_bulk_clear_handler).pack(side="left", padx=15)

# --- Section 4: Start & Execution ---
frame_start = customtkinter.CTkFrame(scroll_bulk, fg_color="transparent")
frame_start.pack(fill="x", padx=30, pady=(20, 10))

# Isolated container for backup toggle
backup_frame = customtkinter.CTkFrame(frame_start, corner_radius=8, fg_color=("gray80", "gray20"))
backup_frame.pack(pady=(0, 15))
var_bulk_backup = customtkinter.BooleanVar(value=True)
customtkinter.CTkCheckBox(backup_frame, text=texts.get("lbl_backup", "Keep Original File as Backup (.orig)"), font=("Arial", 13), variable=var_bulk_backup).pack(padx=20, pady=10)

# Primary execution button
btn_bulk_go = customtkinter.CTkButton(frame_start, text=texts.get("btn_start_bulk", "Vorschau & Simulation"), font=("Arial", 18, "bold"), fg_color="#8b0000", hover_color="#5a0000", height=50, corner_radius=8, command=simulate_bulk_process)
btn_bulk_go.pack(pady=5, fill="x", padx=150)

# Progress visualization
bulk_prog_bar = customtkinter.CTkProgressBar(frame_start, height=12, corner_radius=5)
bulk_prog_bar.pack(fill="x", padx=40, pady=15); bulk_prog_bar.set(0)
lbl_bulk_status = customtkinter.CTkLabel(frame_start, text="", font=("Arial", 12))
lbl_bulk_status.pack()

# --- Application Startup ---
status_frame = customtkinter.CTkFrame(app, height=30, corner_radius=0)
status_frame.pack(side="bottom", fill="x")
lbl_status_main = customtkinter.CTkLabel(status_frame, text="", font=("Arial", 12, "bold"))
lbl_status_main.pack(side="left", padx=20)

system_ready = update_main_status()

if not os.path.exists(config.CONFIG_FILE) or not system_ready:
    app.after(100, show_setup_wizard)

# check for update
threading.Thread(target=check_for_updates, daemon=True).start()

# --- Linux Mousewheel Fix ---
def on_linux_scroll(event):
    # mousewheel -> button events
    direction = -1 if event.num == 4 else 1
    
    # Get underlaying element
    widget = app.winfo_containing(event.x_root, event.y_root)
    
    # Move scrollbar
    while widget:
        if widget.winfo_class() == "Canvas":
            if widget.cget("yscrollcommand"):
                widget.yview_scroll(direction, "units")
                return
        widget = widget.master

# Linux only
if platform.system() == "Linux":
    app.bind_all("<Button-4>", on_linux_scroll)
    app.bind_all("<Button-5>", on_linux_scroll)

app.mainloop()