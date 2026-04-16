import platform
from gui.app import MediaFixerApp

def on_mousewheel(event, app):
    """ Global OS-specific mousewheel handler """
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

if __name__ == "__main__":
    app = MediaFixerApp()
    
    # Bind scroll globally across OS
    if platform.system() == "Linux":
        app.bind_all("<Button-4>", lambda e: on_mousewheel(e, app))
        app.bind_all("<Button-5>", lambda e: on_mousewheel(e, app))
    else:
        app.bind_all("<MouseWheel>", lambda e: on_mousewheel(e, app))

    app.mainloop()