import winreg
import os
import shutil

def optimize_cs2(log_success, log_error, log_info):
    log_info("Применение CS2 Оптимизаций (Autoexec + Binds)...")
    try:
        cs2_cfg_path = r"C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\game\csgo\cfg\autoexec.cfg"
        os.makedirs(os.path.dirname(cs2_cfg_path), exist_ok=True)
        if os.path.isfile(cs2_cfg_path):
            backup_path = os.path.join(os.path.dirname(cs2_cfg_path), "autoexec.winboost-backup.cfg")
            shutil.copy2(cs2_cfg_path, backup_path)
            log_info(f"Существующий autoexec.cfg сохранён: {backup_path}")
        
        cs2_config = """// ==========================================
// CS2 Optimized Config by WinBoost
// ==========================================

// --- Optimization & Network ---
fps_max "0"                                  // Убирает лимит FPS
rate "786432"                                // Максимальный рейт для стабильного соединения
cl_updaterate "128"
cl_interp "0.015625"
cl_hud_telemetry_frametime_show "2"          // Показывает пинг и фпс в случае проблем
cl_hud_telemetry_ping_show "2"
cl_hud_telemetry_net_misdelivery_show "2"

// --- Viewmodel (Руки) ---
viewmodel_fov "68"
viewmodel_offset_x "2.5"
viewmodel_offset_y "0"
viewmodel_offset_z "-1.5"
viewmodel_presetpos "3"

// --- Radar (Радар) ---
cl_radar_always_centered "0"
cl_radar_scale "0.4"
cl_hud_radar_scale "1.15"
cl_radar_icon_scale_min "0.6"
cl_radar_rotate "1"

// --- Binds: Buy (Быстрая покупка) ---
// Стрелочки для покупки основного оружия:
bind "uparrow" "buy ak47; buy m4a1;"         // Стрелка ВВЕРХ: AK-47 (за Т) / M4A4 (за КТ)
bind "downarrow" "buy m4a1_silencer;"        // Стрелка ВНИЗ: M4A1-S (за КТ)

// Покупка гранат на одну кнопку (\\) - приоритет на Молотов/Дым:
bind "\\" "buy incgrenade; buy molotov; buy smokegrenade; buy hegrenade; buy flashbang; buy flashbang;"

// Полезные бинды:
bind "mwheelup" "+jump"
bind "C" "use weapon_c4; drop"

host_writeconfig
echo "WinBoost CS2 Config Loaded!"
"""
        with open(cs2_cfg_path, 'w', encoding='utf-8') as f:
            f.write(cs2_config)
            
        log_success("Файл autoexec.cfg успешно создан и бинды на покупку гранат применены.")
        
        # CPU Priority
        key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\cs2.exe\PerfOptions"
        key = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "CpuPriorityClass", 0, winreg.REG_DWORD, 3) # High Priority
        winreg.CloseKey(key)
        log_success("Приоритет CPU для CS2 установлен на 'Высокий'.")
        
    except Exception as e:
        log_error(f"Ошибка при настройке CS2: {e}")

def get_category(log_success, log_error, log_info):
    return {
        'title': '🎮 CS2 Оптимизация',
        'desc': 'Киберспортивный конфиг и высокий приоритет',
        'actions': [{
            'name': 'Оптимизировать CS2 (Autoexec + Binds)',
            'desc': 'Создает киберспортивный autoexec.cfg и ставит высокий приоритет',
            'run': lambda: optimize_cs2(log_success, log_error, log_info),
            'icon': '🔫',
            'risk': 'yellow',
            'irreversible': True,
            'effects': {'registry': [{
                'hive': winreg.HKEY_LOCAL_MACHINE,
                'path': r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\cs2.exe\PerfOptions',
                'name': 'CpuPriorityClass',
            }]},
        }]
    }
