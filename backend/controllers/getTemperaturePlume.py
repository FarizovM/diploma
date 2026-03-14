import numpy as np
import matplotlib.pyplot as plt
import io
import base64

def generate_temperature_plume(lat_source: float, lng_source: float, wind_dir: float, wind_speed: float, air_temp: float, bg_temp: float = 0):
    """
    air_temp: Температура на станції (джерело)
    bg_temp: Фонова температура міста (до якої прагне повітря через теплообмін)
    """
    grid_size = 0.08 # Трохи більша зона для температури
    lat_min, lat_max = lat_source - grid_size, lat_source + grid_size
    lng_min, lng_max = lng_source - grid_size, lng_source + grid_size

    y, x = np.mgrid[lat_min:lat_max:300j, lng_min:lng_max:300j]

    # Вектор вітру
    angle_rad = np.radians((wind_dir + 180) % 360)
    dy_m = (y - lat_source) * 111320
    dx_m = (x - lng_source) * 111320 * np.cos(np.radians(lat_source))

    downwind = dx_m * np.sin(angle_rad) + dy_m * np.cos(angle_rad)
    crosswind = -dx_m * np.cos(angle_rad) + dy_m * np.sin(angle_rad)

    u = max(wind_speed, 0.5)
    downwind_safe = np.clip(downwind, 100, None)
    
    # 1. Дифузія (Теплопровідність): розширення теплового сліду
    # Тепло розсіюється ширше і рівномірніше, ніж пил, тому коефіцієнт більший
    sigma_y = 200 + (0.5 / np.sqrt(u)) * downwind_safe
    
    # 2. Розрахунок впливу (від 0 до 1) за рівнянням адвекції-дифузії
    influence = np.zeros_like(downwind)
    valid = downwind > 0
    
    influence[valid] = (1.0 / (np.sqrt(2 * np.pi) * u * sigma_y[valid] / 500)) * \
                       np.exp(- (crosswind[valid]**2) / (2 * sigma_y[valid]**2))

    # 3. Втрата тепла (охолодження/нагрівання до фонової температури)
    # З відстанню вплив станції експоненційно падає
    decay_rate = 0.0008 / u
    influence[valid] *= np.exp(-decay_rate * downwind[valid])

    # Нормалізуємо вплив так, щоб в епіцентрі він був рівно 1.0
    max_inf = np.max(influence)
    if max_inf > 0:
        influence = influence / max_inf

    # 4. ОБЧИСЛЕННЯ РЕАЛЬНОЇ ТЕМПЕРАТУРИ В КОЖНІЙ ТОЧЦІ
    # T = Фонова температура + (Різниця температур * Коефіцієнт впливу)
    delta_T = air_temp - bg_temp
    temperature_grid = bg_temp + (delta_T * influence)

    # ==========================================
    # ВІЗУАЛІЗАЦІЯ МЕТЕОРОЛОГІЧНОЇ КАРТИ
    # ==========================================
    fig, ax = plt.subplots(figsize=(7, 7), dpi=300)
    ax.axis('off')
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    
    # Використовуємо метеорологічну палітру RdYlBu_r (від синього до червоного)
    cmap = plt.get_cmap('RdYlBu_r')
    
    # Робимо альфа-канал (прозорість) залежним від сили впливу, 
    # щоб фонова температура (там де вплив 0) була повністю прозорою!
    colors = cmap(np.arange(cmap.N))
    alphas = np.clip(influence * 0.85, 0, 0.85) # Прозорість від 0 до 85%
    
    # Малюємо кольорову підкладку температури
    # Фіксуємо межі від -10 до +40 градусів, щоб кольори не стрибали при зміні станцій
    im = ax.imshow(temperature_grid, extent=[lng_min, lng_max, lat_min, lat_max], 
                   origin='lower', cmap='RdYlBu_r', vmin=-10, vmax=40, 
                   interpolation='bicubic', alpha=influence * 0.85)

    # ДОДАЄМО ІЗОТЕРМИ (Лінії однакової температури)
    # Зробимо так, щоб лінії малювалися кожні 0.5 або 1 градус
    if abs(delta_T) > 1:
        step = 0.5 if abs(delta_T) < 5 else 1.0
        # Генеруємо рівні температур між фоном і станцією
        levels = np.arange(min(bg_temp, air_temp), max(bg_temp, air_temp), step)
        if len(levels) > 0:
            contours = ax.contour(x, y, temperature_grid, levels=levels, 
                                  colors='white', linewidths=1.0, alpha=0.7)
            
            # ВАУ-ЕФЕКТ: Підписуємо цифри прямо на лініях (наприклад "18.5°")
            ax.clabel(contours, inline=True, fontsize=8, fmt='%1.1f°')

    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True)
    plt.close(fig)
    
    return {
        "status": 200,
        "result": {
            "image": f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}",
            "bounds": [[lat_min, lng_min], [lat_max, lng_max]]
        }
    }