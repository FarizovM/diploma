import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import io
import base64

def generate_plume_image(lat_source: float, lng_source: float, wind_dir: float, wind_speed: float):
    # 1. Розмір зони (збільшив для гарного довгого шлейфу)
    grid_size = 0.06
    lat_min, lat_max = lat_source - grid_size, lat_source + grid_size
    lng_min, lng_max = lng_source - grid_size, lng_source + grid_size

    # 2. Більш щільна сітка (300x300 пікселів) для високої якості відображення
    y, x = np.mgrid[lat_min:lat_max:300j, lng_min:lng_max:300j]

    # 3. Вектор вітру та геометрія сітки
    angle_rad = np.radians((wind_dir + 180) % 360)
    dy_m = (y - lat_source) * 111320
    dx_m = (x - lng_source) * 111320 * np.cos(np.radians(lat_source))

    downwind = dx_m * np.sin(angle_rad) + dy_m * np.cos(angle_rad)
    crosswind = -dx_m * np.cos(angle_rad) + dy_m * np.sin(angle_rad)

    # 4. Модель (робимо шлейф візуально ширшим)
    Q = 100 
    u = max(wind_speed, 0)

    # Штучно обмежуємо мінімальну відстань для формули на рівні 100 метрів.
    downwind_safe = np.clip(downwind, 100, None)

    # Коефіцієнт розширення
    sigma_y = 100 + (0.3 / np.sqrt(u)) * downwind_safe

    concentration = np.zeros_like(downwind)
    valid = downwind > 0
    
    # Базова формула Гаусса
    concentration[valid] = (Q / (np.sqrt(2 * np.pi) * u * sigma_y[valid])) * \
                           np.exp(- (crosswind[valid]**2) / (2 * sigma_y[valid]**2))

    # Додаємо природне згасання з відстанню. 
    # Базовий коефіцієнт згасання ділимо на швидкість. 
    # Вітер 5 м/с понесе пляму в 5 разів далі, ніж вітер 1 м/с, перш ніж вона розчиниться.
    decay_rate = 0.0006 / u
    concentration[valid] *= np.exp(-decay_rate * downwind[valid])

    # Нормалізація значень (від 0 до 1)
    max_c = np.max(concentration)
    if max_c > 0:
        concentration = concentration / max_c

    # Формуємо зображення
    fig, ax = plt.subplots(figsize=(6, 6), dpi=300) 
    ax.axis('off')
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    
    # Беремо теплову палітру
    base_cmap = plt.get_cmap('turbo')
    cmap_colors = base_cmap(np.arange(base_cmap.N))
    
    # Створюємо математично плавне згасання прозорості (Alpha-каналу)
    # Слабкий вплив ставав 100% прозорим, а епіцентр мав прозорість 85%
    alphas = np.power(np.linspace(0, 1, base_cmap.N), 1.5) * 0.85
    cmap_colors[:, -1] = alphas
    smooth_cmap = LinearSegmentedColormap.from_list("smooth_turbo", cmap_colors)

    # Накладаємо шлейф з інтерполяцією для ідеально шовкового переходу кольорів
    ax.imshow(concentration, extent=[lng_min, lng_max, lat_min, lat_max], 
              origin='lower', cmap=smooth_cmap, interpolation='bicubic')

    # Додаємо ізолінії
    # Вони показуватимуть межі 10%, 30%, 50%, 70% та 90% концентрації
    levels = [0.1, 0.3, 0.5, 0.7, 0.9] 
    ax.contour(x, y, concentration, levels=levels, colors='white', linewidths=0.8, alpha=0.5)

    # Збереження і кодування
    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True)
    plt.close(fig)
    
    base64_img = base64.b64encode(buf.getvalue()).decode('utf-8')
    
    return {
        "status": 200,
        "result": {
            "image": f"data:image/png;base64,{base64_img}",
            "bounds": [[lat_min, lng_min], [lat_max, lng_max]]
        }
    }