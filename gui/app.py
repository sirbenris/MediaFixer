import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import threading
import sv_ttk
import platform

import config
from config import current_config, texts, audio_flags as AUDIO_FLAGS
import media_engine
from gui.components import ScrollableFrame
from core.processor import AudioProcessor

class MediaFixerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.geometry("1100x900")
        self.title(texts.get("app_title", "Media Fixer - Native Edition"))
        sv_ttk.set_theme("dark")

        # Prevent combobox scrolling issues
        self.unbind_class("TCombobox", "<MouseWheel>")
        self.unbind_class("TCombobox", "<Button-4>")
        self.unbind_class("TCombobox", "<Button-5>")

        self.processor = AudioProcessor(self)
        self.bulk_target_folder = ""
        
        self.setup_ui()
        self.startup_sequence()

    def setup_ui(self):
        self._build_top_frame()
        
        self.tabview = ttk.Notebook(self)
        self.tabview.pack(padx=20, pady=(0, 20), fill="both", expand=True)

        self.tab_single = ttk.Frame(self.tabview)
        self.tab_bulk = ttk.Frame(self.tabview)
        self.tabview.add(self.tab_single, text=texts.get("tab_single", "Single File"))
        self.tabview.add(self.tab_bulk, text=texts.get("tab_bulk", "Bulk"))

        self._build_single_tab()
        self._build_bulk_tab()
        self._build_status_bar()

    def _build_top_frame(self):
        top_frame = ttk.Frame(self)
        top_frame.pack(fill="x", pady=10, padx=20)
        self.v_lang_main = tk.StringVar(value=current_config["ui_language"])
        lang_menu = ttk.Combobox(top_frame, values=config.available_languages, textvariable=self.v_lang_main, state="readonly", width=15)
        lang_menu.bind("<<ComboboxSelected>>", self.on_language_changed)
        lang_menu.pack(side="right")

    def _build_single_tab(self):
        self.scroll_single = ScrollableFrame(self.tab_single)
        self.scroll_single.pack(fill="both", expand=True)

        frame_file_ops = ttk.LabelFrame(self.scroll_single.scrollable_frame, text="File Selection", padding=(15, 15))
        frame_file_ops.pack(fill="x", padx=30, pady=10)

        frame_save_mode = ttk.Frame(frame_file_ops)
        frame_save_mode.pack(pady=5)
        self.var_save_mode = tk.StringVar(value="inline")
        ttk.Radiobutton(frame_save_mode, text=texts.get("mode_inline", "Overwrite"), variable=self.var_save_mode, value="inline").pack(side="left", padx=15)
        ttk.Radiobutton(frame_save_mode, text=texts.get("mode_newfile", "Save As"), variable=self.var_save_mode, value="newfile").pack(side="left", padx=15)

        self.btn_select_file = ttk.Button(frame_file_ops, text=texts.get("btn_file", "Select File"), command=self.select_single_file, style="Accent.TButton")
        self.btn_select_file.pack(pady=15)

        self.lbl_selected_file = ttk.Label(frame_file_ops, text=texts.get("lbl_no_file", "-"), font=("Segoe UI", 11, "italic"), foreground="gray")
        self.lbl_selected_file.pack(pady=(0, 5))

        self.frame_inspector = ttk.LabelFrame(self.scroll_single.scrollable_frame, text="Audio Streams", padding=(15, 10))
        self.frame_inspector.pack(fill="both", expand=True, padx=30, pady=10)

        header_frame = ttk.Frame(self.frame_inspector)
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

        self.scroll_table = ScrollableFrame(self.frame_inspector)
        self.scroll_table.pack(padx=0, pady=(10, 15), fill="both", expand=True)
        self.scroll_table.canvas.configure(height=300)

    def _build_bulk_tab(self):
        self.scroll_bulk = ScrollableFrame(self.tab_bulk)
        self.scroll_bulk.pack(fill="both", expand=True)

        frame_bulk_top = ttk.Frame(self.scroll_bulk.scrollable_frame)
        frame_bulk_top.pack(pady=(15, 15))
        self.btn_select_folder = ttk.Button(frame_bulk_top, text=texts.get("btn_folder", "Select Folder"), command=self.select_bulk_folder, style="Accent.TButton")
        self.btn_select_folder.pack(side="left", padx=10)
        self.lbl_bulk_folder = ttk.Label(frame_bulk_top, text="No folder selected", font=("Segoe UI", 11, "italic"), foreground="gray")
        self.lbl_bulk_folder.pack(side="left", padx=10)

        frame_filter = ttk.LabelFrame(self.scroll_bulk.scrollable_frame, text=texts.get("lbl_filter", "1. Filters"), padding=(15, 10))
        frame_filter.pack(fill="x", padx=30, pady=10)

        f_row1 = ttk.Frame(frame_filter)
        f_row1.pack(fill="x", pady=(5, 5))

        ttk.Label(f_row1, text=texts.get("lbl_ext", "Ext:")).pack(side="left")
        self.var_bulk_ext = tk.StringVar(value=texts.get("opt_all_vids", "All Videos"))
        ttk.Combobox(f_row1, values=[texts.get("opt_all_vids", "All Videos"), ".mp4", ".mkv"], textvariable=self.var_bulk_ext, state="readonly", width=12).pack(side="left", padx=10)
        ttk.Label(f_row1, text=texts.get("lbl_contains", "Contains:")).pack(side="left", padx=(10,0))
        self.var_bulk_contains = tk.StringVar(value="")
        ttk.Entry(f_row1, textvariable=self.var_bulk_contains, width=20).pack(side="left", padx=10)
        self.var_bulk_case = tk.BooleanVar(value=False)
        ttk.Checkbutton(f_row1, text=texts.get("chk_case", "Case Sensitive"), variable=self.var_bulk_case).pack(side="left", padx=10)
        self.var_bulk_sub = tk.BooleanVar(value=True)
        ttk.Checkbutton(f_row1, text=texts.get("chk_sub", "Subfolders"), variable=self.var_bulk_sub).pack(side="right", padx=10)

        frame_target = ttk.LabelFrame(self.scroll_bulk.scrollable_frame, text=texts.get("lbl_bulk_target", "2. Apply to? (Conditions)"), padding=(15, 10))
        frame_target.pack(fill="x", padx=30, pady=10)

        t_row1 = ttk.Frame(frame_target)
        t_row1.pack(fill="x", pady=5)

        opt_tracks = [texts.get("opt_all_audio", "All Audio"), texts.get("opt_track_0", "Track #0"), texts.get("opt_track_1", "Track #1"), texts.get("opt_track_custom", "Custom Track #")]
        self.var_bulk_track = tk.StringVar(value=opt_tracks[0])
        cb_track = ttk.Combobox(t_row1, values=opt_tracks, textvariable=self.var_bulk_track, state="readonly", width=20)
        cb_track.bind("<<ComboboxSelected>>", self.on_track_sel_changed)
        cb_track.pack(side="left", padx=5)
        self.var_bulk_track_custom = tk.StringVar(value="0")
        self.entry_bulk_track_custom = ttk.Entry(t_row1, textvariable=self.var_bulk_track_custom, width=5, state="disabled")
        self.entry_bulk_track_custom.pack(side="left", padx=5)
        self.var_bulk_skip = tk.BooleanVar(value=True)
        ttk.Checkbutton(t_row1, text=texts.get("lbl_skip_correct", "Skip if correct"), variable=self.var_bulk_skip).pack(side="left", padx=20)

        t_row2 = ttk.Frame(frame_target)
        t_row2.pack(fill="x", pady=(5, 5))

        self.var_cond_lang_en = tk.BooleanVar(value=False); ttk.Checkbutton(t_row2, text=texts.get("lbl_if_lang", "If Lang:"), variable=self.var_cond_lang_en).pack(side="left", padx=(5,0))
        self.var_cond_lang_val = tk.StringVar(value=config.available_flags[0]); ttk.Combobox(t_row2, values=config.available_flags, textvariable=self.var_cond_lang_val, state="readonly", width=12).pack(side="left", padx=(5, 15))
        self.var_cond_codec_en = tk.BooleanVar(value=False); ttk.Checkbutton(t_row2, text=texts.get("lbl_if_codec", "If Codec:"), variable=self.var_cond_codec_en).pack(side="left", padx=(5,0))
        self.var_cond_codec_val = tk.StringVar(value=config.FILTER_CODEC_OPTIONS[0]); ttk.Combobox(t_row2, values=config.FILTER_CODEC_OPTIONS, textvariable=self.var_cond_codec_val, state="readonly", width=10).pack(side="left", padx=(5, 15))
        self.var_cond_bit_en = tk.BooleanVar(value=False); ttk.Checkbutton(t_row2, text=texts.get("lbl_if_bitrate", "If Bitrate:"), variable=self.var_cond_bit_en).pack(side="left", padx=(5,0))
        self.var_cond_bit_val = tk.StringVar(value=""); ttk.Entry(t_row2, textvariable=self.var_cond_bit_val, width=15).pack(side="left", padx=(5, 15))

        frame_action = ttk.LabelFrame(self.scroll_bulk.scrollable_frame, text=texts.get("lbl_bulk_what", "3. What to do? (Action)"), padding=(15, 10))
        frame_action.pack(fill="x", padx=30, pady=10)

        a_row1 = ttk.Frame(frame_action)
        a_row1.pack(fill="x", pady=5)

        bulk_acts = [texts.get("btn_action_patch", "Patch"), texts.get("btn_action_add", "Add New"), texts.get("btn_action_delete", "Delete")]
        self.var_bulk_act = tk.StringVar(value=bulk_acts[0])
        ttk.Combobox(a_row1, values=bulk_acts, textvariable=self.var_bulk_act, state="readonly", width=15).pack(side="left", padx=2)
        self.var_bulk_lang = tk.StringVar(value=config.available_flags[0])
        ttk.Combobox(a_row1, values=config.available_flags, textvariable=self.var_bulk_lang, state="readonly", width=12).pack(side="left", padx=10)
        self.var_bulk_codec = tk.StringVar(value="Copy")
        ttk.Combobox(a_row1, values=config.CODEC_OPTIONS, textvariable=self.var_bulk_codec, state="readonly", width=8).pack(side="left", padx=2)
        self.var_bulk_bit = tk.StringVar(value="Original")
        ttk.Combobox(a_row1, values=config.BITRATE_OPTIONS, textvariable=self.var_bulk_bit, state="readonly", width=10).pack(side="left", padx=2)
        self.var_bulk_chan = tk.StringVar(value="Original")
        ttk.Combobox(a_row1, values=config.CHANNEL_OPTIONS, textvariable=self.var_bulk_chan, state="readonly", width=15).pack(side="left", padx=2)

        a_row2 = ttk.Frame(frame_action)
        a_row2.pack(fill="x", pady=(5, 5))

        ttk.Label(a_row2, text=texts.get("lbl_set_title", "Set Title:")).pack(side="left", padx=(2, 5))
        self.var_bulk_title = tk.StringVar(value="")
        ttk.Entry(a_row2, textvariable=self.var_bulk_title, width=35).pack(side="left", padx=5)

        self.var_bulk_clear_handler = tk.BooleanVar(value=False)
        ttk.Checkbutton(a_row2, text=texts.get("chk_clear_handler", "Clear Handler Name"), variable=self.var_bulk_clear_handler).pack(side="left", padx=15)

        frame_start = ttk.Frame(self.scroll_bulk.scrollable_frame)
        frame_start.pack(fill="x", padx=30, pady=(20, 10))

        options_row = ttk.Frame(frame_start)
        options_row.pack(fill="x", pady=10)

        self.var_bulk_backup = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_row, text=texts.get("lbl_backup", "Keep Original File as Backup (.orig)"), variable=self.var_bulk_backup).pack(side="left", padx=(150, 20))

        ttk.Label(options_row, text=texts.get("lbl_cpu_load", "CPU Usage:")).pack(side="left", padx=(20, 5))

        self.var_bulk_cpu = tk.StringVar(value=texts.get("opt_cpu_max", "Maximum"))
        cpu_opts = [texts.get("opt_cpu_max", "Maximum"), texts.get("opt_cpu_med", "Medium"), texts.get("opt_cpu_low", "Low")]
        cb_cpu = ttk.Combobox(options_row, values=cpu_opts, textvariable=self.var_bulk_cpu, state="readonly", width=22)
        cb_cpu.pack(side="left")

        self.btn_bulk_go = ttk.Button(frame_start, text=texts.get("btn_start_bulk", "Vorschau & Simulation"), style="Accent.TButton", command=self.processor.simulate_bulk_process)
        self.btn_bulk_go.pack(pady=10, fill="x", padx=150)

        self.bulk_prog_bar = ttk.Progressbar(frame_start, maximum=1.0, mode="determinate")
        self.bulk_prog_bar.pack(fill="x", padx=40, pady=15)
        self.lbl_bulk_status = ttk.Label(frame_start, text="", font=("Segoe UI", 10))
        self.lbl_bulk_status.pack()

    def _build_status_bar(self):
        status_frame = ttk.Frame(self, padding=(20, 5))
        status_frame.pack(side="bottom", fill="x")
        self.lbl_status_main = ttk.Label(status_frame, text="", font=("Segoe UI", 10, "bold"))
        self.lbl_status_main.pack(side="left")

        self.lbl_version = ttk.Label(status_frame, text=f"v{config.APP_VERSION}", font=("Segoe UI", 10), foreground="gray")
        self.lbl_version.pack(side="right")

    def startup_sequence(self):
        system_ready = self.update_main_status()
        if not os.path.exists(config.CONFIG_FILE) or not system_ready:
            self.after(100, self.show_setup_wizard)
        threading.Thread(target=self.processor.check_for_updates, daemon=True).start()

    def update_main_status(self):
        if media_engine.check_ffmpeg_installed():
            self.lbl_status_main.configure(text=texts.get("status_ready", "✅ FFmpeg Ready"), foreground="#4CAF50")
            self.btn_select_file.configure(state="normal")
            self.btn_select_folder.configure(state="normal")
            return True
        self.lbl_status_main.configure(text=texts.get("status_missing", "❌ FFmpeg Missing!"), foreground="#F44336")
        self.btn_select_file.configure(state="disabled")
        self.btn_select_folder.configure(state="disabled")
        return False

    def on_language_changed(self, event=None):
        choice = self.v_lang_main.get()
        if choice == current_config["ui_language"]: return
        current_config["ui_language"] = choice
        config.save_config()
        self.destroy()
        os.execl(sys.executable, sys.executable, *sys.argv)

    def select_single_file(self):
        filepath = filedialog.askopenfilename(
            title=texts.get("dialog_title_video", "Select Video"),
            filetypes=[(texts.get("dialog_filter_video", "Video Files"), "*.mp4 *.mkv"), ("All Files", "*.*")]
        )
        if filepath: self.analyze_file(filepath)

    def select_bulk_folder(self):
        folder = filedialog.askdirectory(title=texts.get("btn_folder", "Select Folder"))
        if folder:
            self.bulk_target_folder = folder
            self.lbl_bulk_folder.configure(text=folder)

    def on_track_sel_changed(self, event):
        if self.var_bulk_track.get() == texts.get("opt_track_custom", "Custom Track #"): self.entry_bulk_track_custom.configure(state="normal")
        else: self.entry_bulk_track_custom.configure(state="disabled")

    def analyze_file(self, filepath):
        for widget in self.scroll_table.scrollable_frame.winfo_children(): widget.destroy()
        self.lbl_selected_file.configure(text=texts.get("lbl_analyzing", "Analyzing..."), foreground="#FFEB3B")
        self.update()
        
        data = media_engine.probe_file(filepath)
        if not data:
            ttk.Label(self.scroll_table.scrollable_frame, text=texts.get("lbl_no_audio", "No Audio found.")).pack(pady=20)
            self.lbl_selected_file.configure(text=os.path.basename(filepath), foreground="white")
            return
            
        streams = data.get("streams", [])
        duration = float(data.get("format", {}).get("duration", 1.0))
        self.lbl_selected_file.configure(text=os.path.basename(filepath), foreground="white")
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
            
            row = ttk.Frame(self.scroll_table.scrollable_frame, style="Card.TFrame")
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
                threading.Thread(target=lambda: self.on_go_clicked(filepath, a, l, c, b, ch, act, tit, clr, rc, btn, len(streams), duration, p_f, p_b, p_l)).start()
            )
            btn_go.pack(side="right", padx=5)

    def on_go_clicked(self, filepath, a_idx, var_lang, var_codec, var_bit, var_chan, var_act, var_title, var_clear, raw_codec, btn, total, dur, p_f, p_b, p_l):
        mode = self.var_save_mode.get()
        target = filepath
        if mode == "newfile":
            target = filedialog.asksaveasfilename(title=texts.get("dialog_save_as", "Save As..."), initialfile=f"fixed_{os.path.basename(filepath)}", defaultextension=".mp4")
            if not target: return
        act_map_rev = {texts.get("btn_action_patch", "Patch"): "Patch", texts.get("btn_action_add", "Add New"): "Add New", texts.get("btn_action_delete", "Delete"): "Delete"}
        
        self.processor.apply_audio_action(filepath, target, a_idx, AUDIO_FLAGS[var_lang.get()], var_codec.get(), var_bit.get(), var_chan.get(), act_map_rev[var_act.get()], var_title.get(), var_clear.get(), raw_codec, btn, total, dur, p_f, p_b, p_l, mode)

    def animate_bulk_ui(self, step=0):
        if not self.processor.bulk_is_working: return
            
        base_btn_text = texts.get("status_processing", "Processing").replace("⏳", "").replace(".", "").strip()
        dots = "." * ((step // 4) % 4)
        spaces = " " * (3 - ((step // 4) % 4))
        self.btn_bulk_go.configure(text=f"{base_btn_text}{dots}{spaces} ⏳")
        
        spinners = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        spinner = spinners[step % len(spinners)]
        if self.processor.bulk_current_file_text:
            self.lbl_bulk_status.configure(text=f"{spinner} {self.processor.bulk_current_file_text}")
            
        self.after(80, self.animate_bulk_ui, step + 1)

    def show_simulation_popup(self, planned_changes):
        if not planned_changes:
            messagebox.showinfo("Info", texts.get("status_bulk_empty", "Empty"))
            return
            
        sim_win = tk.Toplevel(self)
        sim_win.title(texts.get("win_sim_title", "Simulation"))
        sim_win.geometry("800x550")
        sim_win.grab_set()
        
        ttk.Label(sim_win, text=texts.get("lbl_sim_intro", "Planned changes:"), font=("Segoe UI", 16, "bold")).pack(pady=10)
        
        txt = tk.Text(sim_win, width=90, height=20, font=("Consolas", 10), bg="#252525", fg="#FFFFFF", relief="flat")
        txt.pack(padx=10, pady=10)
        for chg in planned_changes: txt.insert("end", f"[{chg['desc']}]  ->  {os.path.basename(chg['filepath'])}\n")
        txt.configure(state="disabled")
        
        btn_frame = ttk.Frame(sim_win)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text=texts.get("btn_sim_cancel", "Cancel"), command=sim_win.destroy).pack(side="left", padx=10)
        ttk.Button(btn_frame, text=texts.get("btn_sim_execute", "Execute Now!"), style="Accent.TButton", command=lambda: self.processor.execute_bulk_process(planned_changes, sim_win)).pack(side="left", padx=10)

    def show_summary_popup(self, successful_files):
        sum_win = tk.Toplevel(self)
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

    def show_setup_wizard(self):
        wizard = tk.Toplevel(self)
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
                    self.update_main_status()
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