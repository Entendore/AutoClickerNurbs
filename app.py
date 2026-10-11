import pygame
import numpy as np
import math
import random
import colorsys
import sys

# --- Constants ---
WIDTH, HEIGHT = 1050, 650
CANVAS_SIZE = 650
GRID_SIZE = 100
CELL_SIZE = CANVAS_SIZE / GRID_SIZE
CENTER = GRID_SIZE / 2
FPS = 60

# Colors
BG_COLOR = (5, 5, 12)
PANEL_COLOR = (18, 18, 30)
TEXT_COLOR = (220, 220, 220)
ACCENT_COLOR = (0, 255, 255)
WARNING_COLOR = (255, 80, 80)
GOLD_COLOR = (255, 215, 0)

# CA Presets
PRESETS = [
    {"name": "Conway", "birth": [3], "survive": [2, 3]},
    {"name": "HighLife", "birth": [3, 6], "survive": [2, 3]},
    {"name": "Seeds", "birth": [2], "survive": []},
    {"name": "Maze", "birth": [3], "survive": [1, 2, 3, 4, 5]},
    {"name": "Replicator", "birth": [1, 3, 5, 7], "survive": [1, 3, 5, 7]},
    {"name": "Coral", "birth": [3], "survive": [4, 5, 6, 7, 8]}
]

# Curated Color Palettes (HSL base hues)
PALETTES = {
    "Cyberpunk": [180, 320, 50, 280, 200],
    "Ocean": [200, 160, 220, 180, 240],
    "Sunset": [20, 0, 40, 300, 340],
    "Forest": [120, 80, 150, 40, 160],
    "Neon": [330, 60, 180, 270, 90]
}

# Layer configuration
LAYERS_CONFIG = [
    {'num_points': 96, 'threshold': 0,  'hue_shift': 0,   'width': 2, 'fill_light': 10, 'node_size': 2},
    {'num_points': 72, 'threshold': 3,  'hue_shift': 30,  'width': 1, 'fill_light': 15, 'node_size': 3},
    {'num_points': 48, 'threshold': 10, 'hue_shift': 60,  'width': 2, 'fill_light': 25, 'node_size': 4},
    {'num_points': 32, 'threshold': 25, 'hue_shift': 180, 'width': 2, 'fill_light': 40, 'node_size': 5},
    {'num_points': 16, 'threshold': 50, 'hue_shift': 210, 'width': 3, 'fill_light': 60, 'node_size': 6}
]

def format_num(n):
    if n < 1000: return f"{int(n)}"
    if n < 1e6: return f"{n/1e3:.1f}K"
    if n < 1e9: return f"{n/1e6:.1f}M"
    if n < 1e12: return f"{n/1e9:.1f}B"
    return f"{n/1e12:.1f}T"

# --- Game State ---
class GameState:
    def __init__(self):
        self.clicks = 0.0
        self.level = 1
        self.auto_clickers = 0
        self.click_power = 1
        self.auto_evolve_level = 0
        self.prestige_multi = 1.0
        
        self.evolve_cost = 100
        self.auto_cost = 50
        self.power_cost = 75
        self.auto_evolve_cost = 500
        self.prestige_cost = 10000
        
        # CA State
        self.grid = self.create_grid()
        self.preset_index = 0
        self.ca_rules = PRESETS[self.preset_index]
        self.symmetry = 4
        
        # Visuals
        self.palette_name = random.choice(list(PALETTES.keys()))
        self.time_speed = random.uniform(-0.5, 0.5)
        self.saturation = random.uniform(70, 100)
        self.rotation_angle = 0.0
        self.evolve_punch = 0.0
        
        # Golden Cell Event
        self.golden_cell = None
        self.golden_timer = random.uniform(15.0, 30.0)

    def create_grid(self):
        return np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.int8)

    def generate_new_visuals(self):
        self.palette_name = random.choice(list(PALETTES.keys()))
        self.time_speed = random.uniform(-0.8, 0.8)
        self.saturation = random.uniform(75, 100)

    def generate_new_ca_rules(self):
        if random.random() > 0.3:
            self.preset_index = random.randint(0, len(PRESETS) - 1)
            self.ca_rules = PRESETS[self.preset_index]
        else:
            complexity = min(2 + self.level // 3, 6)
            birth = sorted(set([random.randint(1, 8) for _ in range(complexity)]))
            survive = sorted(set([random.randint(1, 8) for _ in range(complexity)]))
            self.ca_rules = {"name": "Chaos", "birth": birth, "survive": survive}
            
        self.symmetry = random.choice([2, 4, 6, 8, 12])
        self.evolve_punch = 1.0

    def cycle_preset(self):
        self.preset_index = (self.preset_index + 1) % len(PRESETS)
        self.ca_rules = PRESETS[self.preset_index]
        self.plant_seed()

    def plant_seed(self):
        self.grid = self.create_grid()
        seed_radius = random.randint(5, 12)
        for _ in range(seed_radius * 4):
            r = random.uniform(0, seed_radius)
            a = random.uniform(0, math.pi * 2)
            for i in range(self.symmetry):
                angle = a + (2 * math.pi * i / self.symmetry)
                cx = int(CENTER + math.cos(angle) * r)
                cy = int(CENTER + math.sin(angle) * r)
                if 0 <= cx < GRID_SIZE and 0 <= cy < GRID_SIZE:
                    self.grid[cy, cx] = 1

    def step_ca(self):
        grid = self.grid > 0
        neighbors = np.zeros_like(grid, dtype=np.int8)
        
        neighbors[1:, :] += grid[:-1, :]
        neighbors[:-1, :] += grid[1:, :]
        neighbors[:, 1:] += grid[:, :-1]
        neighbors[:, :-1] += grid[:, 1:]
        
        neighbors[1:, 1:] += grid[:-1, :-1]
        neighbors[1:, :-1] += grid[:-1, 1:]
        neighbors[:-1, 1:] += grid[1:, :-1]
        neighbors[:-1, :-1] += grid[1:, 1:]

        birth_mask = np.isin(neighbors, self.ca_rules['birth']) & ~grid if self.ca_rules['birth'] else False
        survive_mask = np.isin(neighbors, self.ca_rules['survive']) & grid if self.ca_rules['survive'] else False

        new_grid = np.zeros_like(self.grid)
        new_grid[survive_mask] = np.minimum(self.grid[survive_mask] + 1, 100)
        new_grid[birth_mask] = 1
        self.grid = new_grid

    def check_extinction(self):
        if np.sum(self.grid > 0) < 5:
            self.plant_seed()

    def spawn_golden_cell(self):
        cx, cy = random.randint(20, 80), random.randint(20, 80)
        self.golden_cell = {'x': cx, 'y': cy, 'life': 10.0}
        
    def click_golden_cell(self):
        reward = 500 * (self.level + self.prestige_multi)
        self.clicks += reward
        # Massive burst
        for _ in range(5):
            self.evolve_action(burst=True)
        self.golden_cell = None
        self.golden_timer = random.uniform(30.0, 60.0)
        return reward

    def evolve_action(self, burst=False):
        cost = 0 if burst else self.evolve_cost
        if self.clicks >= cost:
            self.clicks -= cost
            if not burst:
                self.level += 1
                self.evolve_cost = int(100 * (1.5 ** self.level))
            self.generate_new_ca_rules()
            self.generate_new_visuals()
            self.plant_seed()

# --- Math & Rendering Helpers ---

def extract_control_points(game, num_points, age_threshold, last_r_cache):
    points = []
    ages = []
    max_radius = int(CENTER - 2)
    last_r = last_r_cache

    for i in range(num_points):
        angle = (i / num_points) * math.pi * 2
        dx, dy = math.cos(angle), math.sin(angle)
        best_r = 0
        best_age = 0
        
        for r in range(1, max_radius):
            px = int(CENTER + dx * r)
            py = int(CENTER + dy * r)
            if 0 <= px < GRID_SIZE and 0 <= py < GRID_SIZE:
                cell_val = game.grid[py, px]
                if cell_val > age_threshold:
                    best_r = r
                    best_age = cell_val
                    
        if best_r == 0:
            best_r = max(last_r * 0.9, 2)
        else:
            last_r = best_r
            
        x = CENTER * CELL_SIZE + dx * best_r * CELL_SIZE
        y = CENTER * CELL_SIZE + dy * best_r * CELL_SIZE
        points.append((x, y))
        ages.append(best_age)
        
    return points, ages, last_r

def rotate_points(points, angle, cx, cy):
    """Rotates a list of 2D points around a center."""
    s, c = math.sin(angle), math.cos(angle)
    rotated = []
    for x, y in points:
        dx, dy = x - cx, y - cy
        rx = cx + (dx * c - dy * s)
        ry = cy + (dx * s + dy * c)
        rotated.append((rx, ry))
    return rotated

def get_bspline_curve_points(pts, samples=12):
    if len(pts) < 4: return []
    res = []
    n = len(pts)
    for i in range(n):
        p0 = pts[(i - 1) % n]
        p1 = pts[i % n]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n]
        
        for t_step in range(samples):
            t = t_step / samples
            t2 = t * t
            t3 = t2 * t
            
            b0 = (1 - 3*t + 3*t2 - t3) / 6.0
            b1 = (4 - 6*t2 + 3*t3) / 6.0
            b2 = (1 + 3*t + 3*t2 - 3*t3) / 6.0
            b3 = t3 / 6.0
            
            x = b0*p0[0] + b1*p1[0] + b2*p2[0] + b3*p3[0]
            y = b0*p0[1] + b1*p1[1] + b2*p2[1] + b3*p3[1]
            res.append((x, y))
    return res

def hsl_to_rgb(h, s, l):
    h, s, l = h/360.0, s/100.0, l/100.0
    r, g, b = colorsys.hls_to_rgb(h, l, s) 
    return (int(r*255), int(g*255), int(b*255))

def draw_glow_polygon(surface, glow_surf, points, color, width=2):
    if len(points) < 3: return
    fill_color = hsl_to_rgb(color[0], color[1], color[2])
    pygame.draw.polygon(surface, fill_color, points)
    
    glow_surf.fill((0, 0, 0, 0))
    rgb_color = hsl_to_rgb(color[0], color[1], color[2] + 10)
    
    pygame.draw.polygon(glow_surf, (*rgb_color, 60), points, width + 8)
    pygame.draw.polygon(glow_surf, (*rgb_color, 30), points, width + 16)
    surface.blit(glow_surf, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    
    pygame.draw.aalines(surface, rgb_color, True, points)
    pygame.draw.lines(surface, rgb_color, True, points, width)

# --- UI & Particles ---
class FloatingText:
    def __init__(self, x, y, text, color):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.life = 1.0
        self.vy = -60

    def update(self, dt):
        self.y += self.vy * dt
        self.life -= dt * 1.5
        return self.life > 0

    def draw(self, screen, font):
        if self.life > 0:
            alpha = max(0, int(self.life * 255))
            text_surf = font.render(self.text, True, self.color)
            text_surf.set_alpha(alpha)
            screen.blit(text_surf, (self.x, self.y))

class Ripple:
    def __init__(self, x, y, color):
        self.x, self.y = x, y
        self.r = 5
        self.life = 1.0
        self.color = color

    def update(self, dt):
        self.r += 80 * dt
        self.life -= dt * 1.2
        return self.life > 0

    def draw(self, screen):
        if self.life > 0:
            alpha = int(max(0, self.life * 255))
            surf = pygame.Surface((int(self.r*2)+10, int(self.r*2)+10), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*self.color, alpha), (int(self.r)+5, int(self.r)+5), int(self.r), 2)
            screen.blit(surf, (self.x - self.r - 5, self.y - self.r - 5))

class AmbientParticle:
    def __init__(self):
        self.x = random.uniform(0, CANVAS_SIZE)
        self.y = random.uniform(0, CANVAS_SIZE)
        self.vx = random.uniform(-10, 10)
        self.vy = random.uniform(-10, 10)
        self.size = random.uniform(0.5, 2.0)
        self.alpha = random.uniform(20, 80)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.x < 0 or self.x > CANVAS_SIZE: self.vx *= -1
        if self.y < 0 or self.y > CANVAS_SIZE: self.vy *= -1

    def draw(self, surf):
        pygame.draw.circle(surf, (150, 150, 200, int(self.alpha)), (int(self.x), int(self.y)), int(self.size))

class Button:
    def __init__(self, x, y, w, h, text, action, cost_key, color=ACCENT_COLOR):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.action = action
        self.cost_key = cost_key
        self.hovered = False
        self.color = color

    def draw(self, screen, font, small_font, game):
        cost = getattr(game, self.cost_key) if self.cost_key else 0
        enabled = game.clicks >= cost
        
        bg_color = self.color if (self.hovered and enabled) else (30, 30, 45)
        if not enabled: bg_color = (20, 20, 30)
        
        pygame.draw.rect(screen, bg_color, self.rect, border_radius=8)
        border_color = self.color if enabled else (60, 60, 80)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=8)
        
        text_surf = font.render(self.text, True, (0,0,0) if (self.hovered and enabled) else (220,220,220))
        screen.blit(text_surf, (self.rect.x + 15, self.rect.y + 10))
        
        if self.cost_key:
            cost_str = format_num(cost)
            cost_surf = small_font.render(cost_str, True, GOLD_COLOR if enabled else (120,120,120))
            screen.blit(cost_surf, (self.rect.right - cost_surf.get_width() - 15, self.rect.y + 14))
            
            if cost > 0:
                progress = min(1.0, game.clicks / cost)
                pygame.draw.rect(screen, (40, 40, 40), (self.rect.x, self.rect.bottom - 4, self.rect.width, 4))
                pygame.draw.rect(screen, self.color, (self.rect.x, self.rect.bottom - 4, self.rect.width * progress, 4))

    def handle_event(self, event, game):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            cost = getattr(game, self.cost_key) if self.cost_key else 0
            if self.hovered and game.clicks >= cost:
                self.action(game)

# --- Button Actions ---
def evolve_action(game):
    game.evolve_action()

def buy_auto_action(game):
    game.clicks -= game.auto_cost
    game.auto_clickers += 1
    game.auto_cost = int(50 * (1.3 ** game.auto_clickers))

def buy_power_action(game):
    game.clicks -= game.power_cost
    game.click_power += 1
    game.power_cost = int(75 * (1.4 ** game.click_power))

def buy_auto_evolve_action(game):
    game.clicks -= game.auto_evolve_cost
    game.auto_evolve_level += 1
    game.auto_evolve_cost = int(500 * (2.5 ** game.auto_evolve_level))

def cycle_preset_action(game):
    game.cycle_preset()

def prestige_action(game):
    if game.clicks >= game.prestige_cost:
        gained = math.floor(math.sqrt(game.clicks / 10000))
        game.prestige_multi += gained * 0.5
        game.clicks = 0
        game.level = 1
        game.auto_clickers = 0
        game.auto_evolve_level = 0
        game.click_power = 1
        game.evolve_cost = 100
        game.auto_cost = 50
        game.power_cost = 75
        game.auto_evolve_cost = 500
        game.prestige_cost = int(10000 * (2 ** (game.prestige_multi - 1)))
        game.generate_new_ca_rules()
        game.generate_new_visuals()
        game.plant_seed()

# --- Main Game Loop ---
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("CA NURBS Morph Clicker Ultra")
    clock = pygame.time.Clock()
    
    font = pygame.font.SysFont("Courier New", 22, bold=True)
    med_font = pygame.font.SysFont("Courier New", 17, bold=True)
    small_font = pygame.font.SysFont("Courier New", 14)
    
    game = GameState()
    game.plant_seed()
    
    ui_x = CANVAS_SIZE + 20
    btn_w = 400
    buttons = [
        Button(ui_x, 220, btn_w, 45, "Morph Shape (Evolve)", evolve_action, "evolve_cost", ACCENT_COLOR),
        Button(ui_x, 275, 190, 45, "Auto-Clicker", buy_auto_action, "auto_cost", (100, 255, 100)),
        Button(ui_x + 210, 275, 190, 45, "Click Power", buy_power_action, "power_cost", (255, 100, 255)),
        Button(ui_x, 330, 190, 40, "Auto-Evolver", buy_auto_evolve_action, "auto_evolve_cost", (100, 200, 255)),
        Button(ui_x + 210, 330, 190, 40, "Cycle CA Preset", cycle_preset_action, None, (255, 165, 0)),
        Button(ui_x, 540, btn_w, 55, "ASCEND (Prestige)", prestige_action, "prestige_cost", GOLD_COLOR)
    ]
    
    canvas_surf = pygame.Surface((CANVAS_SIZE, CANVAS_SIZE))
    glow_surf = pygame.Surface((CANVAS_SIZE, CANVAS_SIZE), pygame.SRCALPHA)
    bg_grid_surf = pygame.Surface((CANVAS_SIZE, CANVAS_SIZE), pygame.SRCALPHA)
    
    floating_texts = []
    ripples = []
    particles = [AmbientParticle() for _ in range(50)]
    
    ca_tick_timer = 0.0
    auto_click_timer = 0.0
    auto_evolve_timer = 0.0
    
    combo_timer = 0.0
    combo_count = 0
    
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        
        # 1. Handle Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            for btn in buttons:
                btn.handle_event(event, game)
                
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if mx < CANVAS_SIZE and my < CANVAS_SIZE:
                    actual_power = game.click_power * game.prestige_multi
                    
                    # Check Golden Cell Click
                    clicked_golden = False
                    if game.golden_cell:
                        gc_screen_x = game.golden_cell['x'] * CELL_SIZE
                        gc_screen_y = game.golden_cell['y'] * CELL_SIZE
                        dist = math.hypot(mx - gc_screen_x, my - gc_screen_y)
                        if dist < 20:
                            reward = game.click_golden_cell()
                            floating_texts.append(FloatingText(mx, my, f"GOLDEN! +{format_num(reward)}", GOLD_COLOR))
                            floating_texts.append(FloatingText(mx, my-30, "MASSIVE BURST!", WARNING_COLOR))
                            game.evolve_punch = 2.0
                            clicked_golden = True
                            
                    if not clicked_golden:
                        game.clicks += actual_power
                        combo_timer = 0.3
                        combo_count += 1
                        
                        txt_color = ACCENT_COLOR
                        burst_radius = 3
                        
                        if combo_count % 5 == 0:
                            actual_power *= 3
                            game.clicks += actual_power * 2
                            txt_color = GOLD_COLOR
                            burst_radius = 6
                            floating_texts.append(FloatingText(mx, my, f"COMBO x{combo_count}!", WARNING_COLOR))
                            
                        floating_texts.append(FloatingText(mx, my - 15, f"+{format_num(actual_power)}", txt_color))
                        ripples.append(Ripple(mx, my, txt_color))
                        
                        gx, gy = int(mx / CELL_SIZE), int(my / CELL_SIZE)
                        for dy in range(-burst_radius, burst_radius + 1):
                            for dx in range(-burst_radius, burst_radius + 1):
                                if abs(dx) + abs(dy) <= burst_radius:
                                    px, py = gx + dx, gy + dy
                                    if 0 <= px < GRID_SIZE and 0 <= py < GRID_SIZE:
                                        game.grid[py, px] = 1

        if combo_timer > 0:
            combo_timer -= dt
            if combo_timer <= 0: combo_count = 0

        # 2. Update Logic
        auto_click_timer += dt
        if game.auto_clickers > 0 and auto_click_timer > 0.1:
            auto_click_timer = 0
            actual_power = (game.auto_clickers * game.prestige_multi)
            game.clicks += actual_power * 0.1
            
            angle = random.uniform(0, math.pi * 2)
            r = random.randint(int(CENTER - 10), int(CENTER + 10))
            px = int(CENTER + math.cos(angle) * r)
            py = int(CENTER + math.sin(angle) * r)
            
            if 0 <= px < GRID_SIZE and 0 <= py < GRID_SIZE:
                game.grid[py, px] = 1
                ripples.append(Ripple(px * CELL_SIZE, py * CELL_SIZE, (100, 255, 100)))

        # Auto Evolver Logic
        if game.auto_evolve_level > 0:
            auto_evolve_timer += dt
            interval = 15.0 / game.auto_evolve_level
            if auto_evolve_timer > interval:
                auto_evolve_timer = 0
                game.evolve_action()

        ca_tick_timer += dt
        if ca_tick_timer > 0.15: 
            ca_tick_timer = 0
            game.step_ca()
            game.check_extinction()

        # Golden Cell Logic
        if game.golden_cell:
            game.golden_cell['life'] -= dt
            if game.golden_cell['life'] <= 0:
                game.golden_cell = None
                game.golden_timer = random.uniform(30.0, 60.0)
        else:
            game.golden_timer -= dt
            if game.golden_timer <= 0:
                game.spawn_golden_cell()

        # Update Visuals
        game.rotation_angle += dt * 0.2
        if game.evolve_punch > 0:
            game.evolve_punch = max(0, game.evolve_punch - dt * 3.5)
            
        floating_texts = [ft for ft in floating_texts if ft.update(dt)]
        ripples = [rp for rp in ripples if rp.update(dt)]
        for p in particles: p.update(dt)

        # 3. Rendering
        screen.fill(BG_COLOR)
        
        # Punch zoom scaling
        scale = 1.0 + (game.evolve_punch * 0.05)
        render_canvas = pygame.transform.smoothscale(canvas_surf, (int(CANVAS_SIZE*scale), int(CANVAS_SIZE*scale)))
        screen.blit(render_canvas, (-(render_canvas.get_width() - CANVAS_SIZE)//2, -(render_canvas.get_height() - CANVAS_SIZE)//2))
        
        # Draw Background Grid (Reactive Color)
        palette = PALETTES[game.palette_name]
        grid_color = hsl_to_rgb(palette[0], 30, 10)
        bg_grid_surf.fill((0,0,0,0))
        for i in range(0, CANVAS_SIZE, 25):
            pygame.draw.line(bg_grid_surf, (*grid_color, 50), (i, 0), (i, CANVAS_SIZE))
            pygame.draw.line(bg_grid_surf, (*grid_color, 50), (0, i), (CANVAS_SIZE, i))
            
        canvas_surf.blit(bg_grid_surf, (0, 0))
        
        fade_surf = pygame.Surface((CANVAS_SIZE, CANVAS_SIZE), pygame.SRCALPHA)
        fade_surf.fill((5, 5, 12, 90)) 
        canvas_surf.blit(fade_surf, (0, 0))
        
        for p in particles: p.draw(canvas_surf)
        for rp in ripples: rp.draw(canvas_surf)

        time_offset = pygame.time.get_ticks() * 0.05 * game.time_speed
        
        # Extract, Rotate, and Draw Layers
        layer_last_r = [25.0] * len(LAYERS_CONFIG) 
        cx, cy = CENTER * CELL_SIZE, CENTER * CELL_SIZE
        
        for i, layer in enumerate(LAYERS_CONFIG):
            pts, ages, last_r = extract_control_points(game, layer['num_points'], layer['threshold'], layer_last_r[i])
            layer_last_r[i] = last_r
            
            # Apply Global Rotation
            rotated_pts = rotate_points(pts, game.rotation_angle, cx, cy)
            
            curve = get_bspline_curve_points(rotated_pts, 12)
            
            if len(curve) > 3:
                base_hue = palette[i % len(palette)]
                hue = (base_hue + time_offset) % 360
                color = (hue, game.saturation, layer['fill_light'])
                draw_glow_polygon(canvas_surf, glow_surf, curve, color, layer['width'])
                
            # Draw Glowing Control Nodes
            node_color = hsl_to_rgb(hue, 100, 70)
            for p_idx, pt in enumerate(rotated_pts):
                # Draw node glow
                glow_surf.fill((0,0,0,0))
                pygame.draw.circle(glow_surf, (*node_color, 100), (int(pt[0]), int(pt[1])), layer['node_size'] + 4)
                canvas_surf.blit(glow_surf, (0,0), special_flags=pygame.BLEND_RGB_ADD)
                # Draw solid core
                pygame.draw.circle(canvas_surf, node_color, (int(pt[0]), int(pt[1])), layer['node_size'])

        # Draw Golden Cell
        if game.golden_cell:
            gx = game.golden_cell['x'] * CELL_SIZE
            gy = game.golden_cell['y'] * CELL_SIZE
            pulse = math.sin(pygame.time.get_ticks() * 0.01) * 5 + 15
            glow_surf.fill((0,0,0,0))
            pygame.draw.circle(glow_surf, (*GOLD_COLOR, 60), (int(gx), int(gy)), int(pulse + 10))
            pygame.draw.circle(glow_surf, (*GOLD_COLOR, 120), (int(gx), int(gy)), int(pulse))
            canvas_surf.blit(glow_surf, (0,0), special_flags=pygame.BLEND_RGB_ADD)
            pygame.draw.circle(canvas_surf, GOLD_COLOR, (int(gx), int(gy)), int(pulse/2))
            pygame.draw.circle(canvas_surf, (255, 255, 255), (int(gx), int(gy)), int(pulse/4))

        # Draw Floating Texts on Screen Space
        for ft in floating_texts: ft.draw(screen, med_font)

        # --- UI PANEL ---
        pygame.draw.rect(screen, PANEL_COLOR, (CANVAS_SIZE, 0, WIDTH - CANVAS_SIZE, HEIGHT))
        pygame.draw.line(screen, (50, 50, 70), (CANVAS_SIZE, 0), (CANVAS_SIZE, HEIGHT), 2)

        title = font.render("NURBS MORPH", True, (255, 255, 255))
        screen.blit(title, (ui_x, 25))
        sub_title = small_font.render(f"PALETTE: {game.palette_name.upper()}", True, ACCENT_COLOR)
        screen.blit(sub_title, (ui_x, 55))
        
        stats = [
            f"Clicks: {format_num(game.clicks)}",
            f"Evolution Level: {game.level}",
            f"Auto-Clickers: {game.auto_clickers}",
            f"Auto-Evolver: Lvl {game.auto_evolve_level}",
            f"Click Power: {format_num(game.click_power * game.prestige_multi)}",
            f"Prestige Multi: x{game.prestige_multi:.1f}"
        ]
        for i, stat in enumerate(stats):
            color = GOLD_COLOR if "Prestige" in stat else TEXT_COLOR
            txt = med_font.render(stat, True, color)
            screen.blit(txt, (ui_x, 90 + i * 22))
            
        if combo_count > 1:
            combo_txt = font.render(f"COMBO x{combo_count}", True, WARNING_COLOR)
            screen.blit(combo_txt, (ui_x, 390))

        info = [
            f"Rule: {game.ca_rules['name']} (B{game.ca_rules['birth']}/S{game.ca_rules['survive']})",
            f"Symmetry: {game.symmetry}-way",
            "Layers: 5 (Age-Traced)",
            "Watch for Golden Cells!"
        ]
        for i, inf in enumerate(info):
            txt = small_font.render(inf, True, (160, 160, 180) if i < 2 else (120, 120, 140))
            screen.blit(txt, (ui_x, 430 + i * 20))

        for btn in buttons:
            btn.draw(screen, med_font, small_font, game)
            
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()