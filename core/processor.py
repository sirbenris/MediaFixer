import os
import shutil
import threading
import subprocess
import re
import time
import urllib.request
import json
import webbrowser
from tkinter import messagebox

import config
from config import current_config, texts, audio_flags as AUDIO_FLAGS
import media_engine

class AudioProcessor:
    """ Handles heavy lifting like FFmpeg processing and background tasks """
    def __init__(self, app):
        self.app = app
        self.bulk_is_working = False
        self.bulk_current_file_text = ""

    def check_for_updates(self):
        if config.APP_VERSION == "dev": return
        try:
            url = "https://api.github.com/repos/sirbenris/MediaFixer/releases/latest"
            req = urllib.request.Request(url, headers={'User-Agent': 'MediaFixer-Update-Check'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                latest_version = data.get("tag_name", "").replace("v", "")
                if latest_version and latest_version != config.APP_VERSION:
                    self.app.after(0, lambda: self.app.lbl_version.configure(
                        text=f"v{config.APP_VERSION} (Update: v{latest_version}!)", 
                        foreground="#FF9800", cursor="hand2"
                    ))
                    self.app.after(0, lambda: self.app.lbl_version.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/sirbenris/MediaFixer/releases/latest")))
                    
                    self.app.after(1500, lambda v=latest_version: self.show_update_popup(v))
        except Exception as e: 
            print(f"Update check failed: {e}")

    def show_update_popup(self, new_version):
        msg = texts.get("update_msg", f"A new version ({new_version}) is available!\nDo you want to download it now?").replace("{v}", new_version)
        if messagebox.askyesno(texts.get("update_title", "Update available!"), msg):
            webbrowser.open("https://github.com/sirbenris/MediaFixer/releases/latest")

    def apply_audio_action(self, orig_path, target_path, a_idx, lang, codec, bitrate, channels, action, title_val, clear_handler, raw_codec, btn, total, duration, p_f, p_b, p_l, mode):
        def task():
            self.app.after(0, lambda: p_f.pack(side="top", fill="x", padx=10, pady=(0, 10)))
            self.app.after(0, lambda: btn.configure(state="disabled", text=texts.get("status_fixing", "Processing...")))
            
            out_file = f"{orig_path}.temp.mp4" if mode == "inline" else target_path
            cmd = [media_engine.FFMPEG_CMD, "-nostdin", "-i", orig_path, "-map", "0", "-c", "copy"]

            if action == "Delete": cmd += ["-map", f"-0:a:{a_idx}"]
            elif action == "Patch":
                c_val = codec.lower() if codec != "Copy" else "copy"
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

            try:
                cpu_choice = self.app.var_bulk_cpu.get()
                if cpu_choice == texts.get("opt_cpu_med", "Medium"):
                    cores = max(1, (os.cpu_count() or 4) // 2)
                    cmd += ["-threads", str(cores)]
                elif cpu_choice == texts.get("opt_cpu_low", "Low"):
                    cmd += ["-threads", "1"]   
            except AttributeError:
                pass 

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
                        self.app.after(0, lambda p=pct: (p_b.configure(value=p), p_l.configure(text=f"{int(p*100)}%")))
                process.wait()
                if process.returncode == 0:
                    shutil.copystat(orig_path, out_file)
                    if mode == "inline":
                        os.remove(orig_path)
                        os.rename(out_file, orig_path)
                    self.app.after(0, lambda: btn.configure(text=texts.get("status_success", "✅ Done!")))
                    self.app.after(1000, self.app.analyze_file, orig_path if mode == "inline" else target_path)
                else: raise Exception("FFmpeg error")
            except Exception as e:
                self.app.after(0, lambda: btn.configure(text=texts.get("status_failed", "❌ Error!"), state="normal"))
                if mode == "inline" and os.path.exists(out_file): os.remove(out_file)

        threading.Thread(target=task, daemon=True).start()

    def match_bulk_streams(self, filepath):
        data = media_engine.probe_file(filepath)
        if not data: return [], 0
        streams = data.get("streams", [])
        target_tracks = []
        track_sel = self.app.var_bulk_track.get()
        
        if track_sel == texts.get("opt_track_0", "Track #0"): target_tracks = [0]
        elif track_sel == texts.get("opt_track_1", "Track #1"): target_tracks = [1]
        elif track_sel == texts.get("opt_track_custom", "Custom Track #"):
            try: 
                val = self.app.var_bulk_track_custom.get().strip()
                if val.isdigit(): target_tracks = [int(val)]
            except: pass

        matched = []
        for a_idx, stream in enumerate(streams):
            if track_sel != texts.get("opt_all_audio", "All Audio") and a_idx not in target_tracks: continue
            tags = stream.get("tags", {})
            if self.app.var_cond_lang_en.get() and tags.get("language", "und") != AUDIO_FLAGS.get(self.app.var_cond_lang_val.get(), "und"): continue
            if self.app.var_cond_codec_en.get() and stream.get("codec_name", "unk").upper() != self.app.var_cond_codec_val.get(): continue
            if self.app.var_cond_bit_en.get():
                bps = stream.get("bit_rate") or tags.get("BPS")
                kbps = str(int(bps)//1000) if str(bps).isdigit() else ""
                target_bps = self.app.var_cond_bit_val.get().strip()
                if target_bps and target_bps != kbps: continue

            if self.app.var_bulk_skip.get() and self.app.var_bulk_act.get() == texts.get("btn_action_patch", "Patch"):
                already_lang = tags.get("language", "und") == AUDIO_FLAGS.get(self.app.var_bulk_lang.get(), "und")
                already_codec = (self.app.var_bulk_codec.get() == "Copy") or (stream.get("codec_name", "unk").upper() == self.app.var_bulk_codec.get().upper())
                already_title = (not self.app.var_bulk_title.get()) or (tags.get("title", "") == self.app.var_bulk_title.get())
                already_handler = (not self.app.var_bulk_clear_handler.get()) or ("handler_name" not in tags)
                if already_lang and already_codec and already_title and already_handler: continue

            matched.append(a_idx)
        return matched, len(streams)

    def simulate_bulk_process(self):
        if not self.app.bulk_target_folder: 
            messagebox.showwarning(texts.get("warn_title", "Warning"), texts.get("warn_no_folder", "Please select a folder first!"))
            return
        if self.app.var_bulk_track.get() == texts.get("opt_all_audio", "All Audio Streams"):
            if not messagebox.askyesno(texts.get("warn_title", "Warning"), texts.get("warn_all_audio", "Modify EVERY matching track?")): return
        do_backup = self.app.var_bulk_backup.get()
        if not do_backup:
            if not messagebox.askyesno(texts.get("warn_title", "Warning"), texts.get("warn_msg", "Proceed without backups?")): return

        def task():
            self.app.after(0, lambda: self.app.btn_bulk_go.configure(state="disabled", text=texts.get("status_bulk_scan", "Scanning... ⏳")))
            self.app.after(0, lambda: self.app.lbl_bulk_status.configure(text=texts.get("status_bulk_scan", "Scanning..."), foreground="#FFEB3B"))
            self.app.after(50, lambda: self.app.scroll_bulk.canvas.yview_moveto(1.0)) 
            
            target_ext = self.app.var_bulk_ext.get()
            name_filter = self.app.var_bulk_contains.get()
            if not self.app.var_bulk_case.get(): name_filter = name_filter.lower()
            action = self.app.var_bulk_act.get()
            target_lang_code = AUDIO_FLAGS.get(self.app.var_bulk_lang.get(), "und")
            codec_val = self.app.var_bulk_codec.get()
            title_val = self.app.var_bulk_title.get()
            clear_handler = self.app.var_bulk_clear_handler.get()
            
            files_to_process = []
            if self.app.var_bulk_sub.get():
                for root, dirs, files in os.walk(self.app.bulk_target_folder):
                    for f in files: files_to_process.append(os.path.join(root, f))
            else:
                for f in os.listdir(self.app.bulk_target_folder):
                    filepath = os.path.join(self.app.bulk_target_folder, f)
                    if os.path.isfile(filepath): files_to_process.append(filepath)

            filtered_files = []
            for f in files_to_process:
                ext = os.path.splitext(f)[1].lower()
                if target_ext in [".mp4", ".mkv"] and ext != target_ext: continue
                if target_ext not in [".mp4", ".mkv"] and ext not in [".mp4", ".mkv"]: continue
                fname_check = os.path.basename(f)
                if not self.app.var_bulk_case.get(): fname_check = fname_check.lower()
                if name_filter and name_filter not in fname_check: continue
                filtered_files.append(f)

            if not filtered_files:
                self.app.after(0, lambda: self.app.lbl_bulk_status.configure(text=texts.get("status_bulk_empty", "Empty"), foreground="#FF9800"))
                self.app.after(0, lambda: self.app.btn_bulk_go.configure(state="normal", text=texts.get("btn_start_bulk", "Vorschau & Simulation")))
                return

            self.app.after(0, lambda: self.app.bulk_prog_bar.configure(value=0))
            total_files = len(filtered_files)
            planned_changes = []

            for i, filepath in enumerate(filtered_files):
                matched_indices, total_audio = self.match_bulk_streams(filepath)
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
                self.app.after(0, lambda p=(i+1)/total_files: self.app.bulk_prog_bar.configure(value=p))

            self.app.after(0, lambda: self.app.show_simulation_popup(planned_changes))
            self.app.after(0, lambda: self.app.lbl_bulk_status.configure(text="Scan complete.", foreground="white"))
            self.app.after(0, lambda: self.app.btn_bulk_go.configure(state="normal", text=texts.get("btn_start_bulk", "Vorschau & Simulation")))

        threading.Thread(target=task, daemon=True).start()

    def execute_bulk_process(self, planned_changes, sim_win):
        sim_win.destroy()
        do_backup = self.app.var_bulk_backup.get()
        
        def task():
            self.bulk_is_working = True
            
            self.app.after(0, lambda: self.app.btn_bulk_go.configure(state="disabled"))
            self.app.after(0, lambda: self.app.bulk_prog_bar.configure(value=0))
            self.app.after(50, lambda: self.app.scroll_bulk.canvas.yview_moveto(1.0)) 
            self.app.after(0, self.app.animate_bulk_ui) 
            
            total = len(planned_changes)
            successful_files = []
            start_time = time.time()
            
            for i, chg in enumerate(planned_changes):
                filepath = chg['filepath']
                desc = chg['desc']
                matched_indices = chg['matched_indices']
                total_audio = chg['total_audio']
                
                if i > 0:
                    elapsed = time.time() - start_time
                    avg_time = elapsed / i
                    remaining = total - i
                    eta_seconds = int(avg_time * remaining)
                    m, s = divmod(eta_seconds, 60)
                    eta_str = texts.get("lbl_eta", "ETA: {m}m {s}s").replace("{m}", str(m)).replace("{s}", str(s).zfill(2))
                else:
                    eta_str = texts.get("lbl_eta_calc", "Calculating ETA...")
                    
                def update_text(d=desc, f=os.path.basename(filepath), e=eta_str):
                    self.bulk_current_file_text = f"[{e}] {d} : {f}"
                self.app.after(0, update_text)
                
                file_data = media_engine.probe_file(filepath)
                streams = file_data.get("streams", []) if file_data else []
                target_lang_code = AUDIO_FLAGS.get(self.app.var_bulk_lang.get(), "und")
                action = self.app.var_bulk_act.get()
                title_val = self.app.var_bulk_title.get()
                clear_handler = self.app.var_bulk_clear_handler.get()
                
                out_file = f"{filepath}.temp.mp4"
                cmd = [media_engine.FFMPEG_CMD, "-nostdin", "-i", filepath, "-map", "0", "-c", "copy"]

                if action == texts.get("btn_action_delete", "Delete"):
                    for t_idx in matched_indices: cmd += ["-map", f"-0:a:{t_idx}"]
                elif action == texts.get("btn_action_patch", "Patch"):
                    for t_idx in matched_indices:
                        raw_codec = streams[t_idx].get("codec_name", "aac") if t_idx < len(streams) else "aac"
                        c_val = self.app.var_bulk_codec.get().lower() if self.app.var_bulk_codec.get() != "Copy" else "copy"
                        if c_val == "copy" and (self.app.var_bulk_bit.get() != "Original" or self.app.var_bulk_chan.get() != "Original"): c_val = raw_codec
                        cmd += [f"-c:a:{t_idx}", c_val]
                        if self.app.var_bulk_bit.get() != "Original": cmd += [f"-b:a:{t_idx}", self.app.var_bulk_bit.get()]
                        if self.app.var_bulk_chan.get() == "Stereo Downmix": cmd += [f"-ac:a:{t_idx}", "2"]
                        cmd += [f"-metadata:s:a:{t_idx}", f"language={target_lang_code}"]
                        if title_val: cmd += [f"-metadata:s:a:{t_idx}", f"title={title_val}"]
                        if clear_handler: cmd += [f"-metadata:s:a:{t_idx}", "handler_name="]
                elif action == texts.get("btn_action_add", "Add New"):
                    for idx_offset, t_idx in enumerate(matched_indices):
                        new_idx = total_audio + idx_offset
                        raw_codec = streams[t_idx].get("codec_name", "aac") if t_idx < len(streams) else "aac"
                        cmd += ["-map", f"0:a:{t_idx}"]
                        c_val = self.app.var_bulk_codec.get().lower() if self.app.var_bulk_codec.get() != "Copy" else "copy"
                        if c_val == "copy" and (self.app.var_bulk_bit.get() != "Original" or self.app.var_bulk_chan.get() != "Original"): c_val = raw_codec
                        cmd += [f"-c:a:{new_idx}", c_val]
                        if self.app.var_bulk_bit.get() != "Original": cmd += [f"-b:a:{new_idx}", self.app.var_bulk_bit.get()]
                        if self.app.var_bulk_chan.get() == "Stereo Downmix": cmd += [f"-ac:a:{new_idx}", "2"]
                        cmd += [f"-metadata:s:a:{new_idx}", f"language={target_lang_code}"]
                        if title_val: cmd += [f"-metadata:s:a:{new_idx}", f"title={title_val}"]
                        if clear_handler: cmd += [f"-metadata:s:a:{new_idx}", "handler_name="]

                try:
                    cpu_choice = self.app.var_bulk_cpu.get()
                    if cpu_choice == texts.get("opt_cpu_med", "Medium"):
                        cores = max(1, (os.cpu_count() or 4) // 2)
                        cmd += ["-threads", str(cores)]
                    elif cpu_choice == texts.get("opt_cpu_low", "Low"):
                        cmd += ["-threads", "1"]
                except AttributeError:
                    pass 

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
                    
                self.app.after(0, lambda p=(i+1)/total: self.app.bulk_prog_bar.configure(value=p))
                
            self.bulk_is_working = False
            self.bulk_current_file_text = ""
            self.app.after(0, lambda: self.app.btn_bulk_go.configure(state="normal", text=texts.get("btn_start_bulk", "Vorschau & Simulation")))
            self.app.after(0, lambda: self.app.lbl_bulk_status.configure(text=texts.get("status_bulk_done", "Done!").replace("{count}", str(len(successful_files))), foreground="#4CAF50"))
            self.app.after(0, lambda: self.app.show_summary_popup(successful_files))

        threading.Thread(target=task, daemon=True).start()