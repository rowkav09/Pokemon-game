#libraries

import sys
from pygame import mouse
import pygame
import random
import math

#functions
def reset_pokemon_spawn():
    global pokemon_caught, caught_time, pokemon_x, pokemon_y, pokemon_frame
    pokemon_caught = False
    caught_time = 0
    pokemon_x, pokemon_y =  random.randint(200,x-200), random.randint(200,y-200)     #choose random coordinates for it to spawn at
    while (trainer_x - 100 < pokemon_x < trainer_x + 100) and (trainer_y - 100 < pokemon_y < trainer_y + 100):  #make sure it doesnt spawn on trainer
        pokemon_x, pokemon_y = random.randint(200, x - 200), random.randint(200, y - 200)# new random position
    pokemon_frame = random.choice(pokemon_pool)  # new random pokemon




#variables
x, y = 800, 700
tile_width = x/2
tile_height = y/2
clicked = False
trainer_x, trainer_y = 375.0, 300.0       #trainer start coordinates
trainer_speed = 0.3                        #walk speed (pixels per ms)
trainer_width, trainer_height = 120,140    #trainer proportions
trainer_frame_width, trainer_frame_height = 121, 126      #actual frame size (sprites don't start at 0,0)
trainer_frame_offset_x, trainer_frame_offset_y = 177, 45  #black padding offset in sprite sheet
facing = 'down'
animation_speed = 0.005                    #animation speed (frames per ms)
frame_index = 0.0                          #initialise frame index
pokemon_frame_offset_y = 0
pokemon_frame_offset_x = 0
pokemon_frame_width = 210
pokemon_frame_height = 228
pokemon_width, pokemon_height = 90, 100
pokeball_thrown = False
pokeball_height, pokeball_width = 20,20
pokeball_flip = False
pokemon_caught = False
throw_start = 0                            #tracks when the pokeball was thrown
pokeball_count = 5
caught_time = 0
pokedex_unlocked = False
pokedex_open = False
scroll_y = 0
pokemon_names = [
    "Bulbasaur", "Ivysaur", "Venusaur", "Charmander", "Charmeleon", "Charizard",
    "Squirtle", "Wartortle", "Blastoise", "Caterpie", "Metapod", "Butterfree",
    "Weedle", "Kakuna", "Beedrill", "Pidgey", "Pidgeotto", "Pidgeot",
    "Rattata", "Raticate", "Spearow", "Fearow", "Ekans", "Arbok",
    "Pikachu", "Raichu"
]  # Example names, adjust to match your sprites

# Track caught Pokémon by index
caught_pokemon = set()

# --- Multiple Pokémon state ---
NUM_POKEMON = 5

# Rarity: lower = rarer
# Clamp rarity and names to match number of loaded sprites
num_sprites = len(pokemon_pool) if 'pokemon_pool' in locals() else 24
pokemon_rarity = [1,1,1,2,2,2,2,2,2,3,3,3,3,3,3,4,4,4,5,5,5,6,6,7,8,10][:num_sprites]
pokemon_names = pokemon_names[:num_sprites]


#initialisation
pygame.init()
pygame.display.set_caption('Pokemon game')
screen = pygame.display.set_mode((x, y))
font = pygame.font.SysFont(name="Arcade Classic", size=90)
clock = pygame.time.Clock()               #clock for delta time

#load images (after display is initialized)
background = pygame.image.load("maps/grassy.jpg")
background = pygame.transform.scale(background, (tile_width, tile_height))
trainer_sheet = pygame.image.load("images/trainer_sheet.png").convert_alpha()
animations = {'down':[],'left':[],'right':[],'up':[]}
direction_rows = {0:'down', 1:'left', 2:'right', 3:'up'}
for row in range(4):
    direction = direction_rows[row]
    for col in range(4):
        frame = trainer_sheet.subsurface(pygame.Rect(
            trainer_frame_offset_x + col * trainer_frame_width,
            trainer_frame_offset_y + row * trainer_frame_height,
            trainer_frame_width,
            trainer_frame_height
        ))
        frame = pygame.transform.scale(frame, (trainer_width, trainer_height))  #pre-scale once
        animations[direction].append(frame)
pokemon_sheet = pygame.image.load("images/3d_starter_sheet.png").convert_alpha()
pokemon_pool = []
for row in range(4):
    for col in range(6):
        frame = pokemon_sheet.subsurface(pygame.Rect(
            pokemon_frame_offset_x + col * pokemon_frame_width,
            pokemon_frame_offset_y + row * pokemon_frame_height,
            pokemon_frame_width, pokemon_frame_height
        ))
        frame = pygame.transform.scale(frame, (pokemon_width, pokemon_height))  #pre-scale once
        pokemon_pool.append(frame)

#pokeball
pokeball = pygame.image.load("images/pokeball.png").convert_alpha()
pokeball = pygame.transform.scale(pokeball, (pokeball_width, pokeball_height))

# choose a random pokemon to appear (from pool)
pokemon_frame = random.choice(pokemon_pool)
if random.randint(0, 1):
    pokeball_flip = True
    pokemon_frame = pygame.transform.flip(pokemon_frame, True, False)  # horizontal flip only

# Now define spawn_pokemon and pokemon_list (after pokemon_pool exists)
def spawn_pokemon():
    # Only spawn in grass area (centered, not edges)
    for _ in range(NUM_POKEMON):
        while True:
            idx = random.choices(range(len(pokemon_pool)), weights=[1/r for r in pokemon_rarity], k=1)[0]
            px = random.randint(120, x-120)
            py = random.randint(120, y-120)
            # Avoid trainer spawn
            if not (trainer_x - 100 < px < trainer_x + 100 and trainer_y - 100 < py < trainer_y + 100):
                break
        direction = random.choice([(1,0),(-1,0),(0,1),(0,-1)])
        speed = random.uniform(0.1,0.3)
        yield {
            'idx': idx,
            'x': px,
            'y': py,
            'dx': direction[0]*speed,
            'dy': direction[1]*speed,
            'frame': pokemon_pool[idx],
            'moving': True
        }
pokemon_list = list(spawn_pokemon())

# Catch mini-game state
catch_scene = False
catch_animating = False
catch_pokeball_pos = None
catch_pokeball_vel = None
catch_pokeball_start = None
catch_pokeball_target = None
catch_dragging = False
catch_result = None
catch_anim_time = 0

#initialisation
pygame.init()
pygame.display.set_caption('Pokemon game')
screen = pygame.display.set_mode((x, y))
font = pygame.font.SysFont(name="Arcade Classic", size=90)
clock = pygame.time.Clock()               #clock for delta time


#load images (after display is initialized)
#map
background = None
trainer_sheet = None
animations = {'down':[],'left':[],'right':[],'up':[]}
direction_rows = {0:'down', 1:'left', 2:'right', 3:'up'}
pokemon_sheet = None
pokemon_pool = []

# ...existing code...

#initialisation
pygame.init()
pygame.display.set_caption('Pokemon game')
screen = pygame.display.set_mode((x, y))
font = pygame.font.SysFont(name="Arcade Classic", size=90)
clock = pygame.time.Clock()               #clock for delta time

# Now load images
background = pygame.image.load("maps/grassy.jpg")
background = pygame.transform.scale(background, (tile_width, tile_height))
trainer_sheet = pygame.image.load("images/trainer_sheet.png").convert_alpha()
for row in range(4):
    direction = direction_rows[row]
    for col in range(4):
        frame = trainer_sheet.subsurface(pygame.Rect(
            trainer_frame_offset_x + col * trainer_frame_width,
            trainer_frame_offset_y + row * trainer_frame_height,
            trainer_frame_width,
            trainer_frame_height
        ))
        frame = pygame.transform.scale(frame, (trainer_width, trainer_height))  #pre-scale once
        animations[direction].append(frame)
pokemon_sheet = pygame.image.load("images/3d_starter_sheet.png").convert_alpha()
for row in range(4):
    for col in range(6):
        frame = pokemon_sheet.subsurface(pygame.Rect(
            pokemon_frame_offset_x + col * pokemon_frame_width,
            pokemon_frame_offset_y + row * pokemon_frame_height,
            pokemon_frame_width, pokemon_frame_height
        ))
        frame = pygame.transform.scale(frame, (pokemon_width, pokemon_height))  #pre-scale once
        pokemon_pool.append(frame)
pokemon_frame = random.choice(pokemon_pool)  # choose a random pokemon to appear (from pool)
if random.randint(0, 1):
    pokeball_flip = True
    pokemon_frame = pygame.transform.flip(pokemon_frame, True, False)  # horizontal flip only
    #pokeball
pokeball = pygame.image.load("images/pokeball.png").convert_alpha()
pokeball = pygame.transform.scale(pokeball, (pokeball_width, pokeball_height))

#event loop
while True:

    # CATCH MINI-GAME SCENE



    if catch_scene:
        dt = clock.tick_busy_loop(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    catch_scene = False
            if not catch_animating and event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mx, my = mouse.get_pos()
                    # Pokeball drag start
                    if (catch_pokeball_pos[0] - 40 < mx < catch_pokeball_pos[0] + 40 and
                        catch_pokeball_pos[1] - 40 < my < catch_pokeball_pos[1] + 40):
                        catch_dragging = True
                        drag_start = (mx, my)
                        catch_drag_start = (mx, my)
            if not catch_animating and event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and catch_dragging:
                    mx, my = mouse.get_pos()
                    # Calculate throw velocity based on drag (slower for easier aim)
                    dx = (mx - catch_drag_start[0]) / 4.0
                    dy = (my - catch_drag_start[1]) / 4.0
                    catch_pokeball_vel = [dx, dy]
                    catch_animating = True
                    catch_anim_time = 0
                    catch_dragging = False

        # Animated background and sparkles (same as before)
        t = pygame.time.get_ticks() / 1000.0
        for i in range(0, x, 40):
            for j in range(0, y, 40):
                color = (
                    int(60+40*(1+math.sin(t+i*0.01+j*0.02))),
                    int(120+60*math.sin(t+i*0.02-j*0.01)),
                    80)
                pygame.draw.rect(screen, color, (i, j, 40, 40))
        for s in range(20):
            sx = int(x/2 + math.sin(t*2+s)*200 + math.sin(t*3+s*2)*30)
            sy = int(y/2 + math.cos(t*2+s)*120 + math.cos(t*3+s*2)*20)
            pygame.draw.circle(screen, (255,255,255,100), (sx, sy), 2)

        # Draw instructions
        font_instr = pygame.font.SysFont("couriernew", 28, bold=True)
        instr = font_instr.render("Drag and flick the Pokéball to catch!", True, (255,255,255))
        screen.blit(instr, (x//2 - instr.get_width()//2, 20))

        # Show aiming arc/guide if dragging
        if catch_dragging:
            mx, my = mouse.get_pos()
            pygame.draw.line(screen, (255,255,0), (catch_pokeball_pos[0], catch_pokeball_pos[1]), (mx, my), 4)
            # Draw a simple arc preview
            for t_arc in range(0, 20):
                px = int(catch_pokeball_pos[0] + (mx-catch_pokeball_pos[0]) * t_arc/20)
                py = int(catch_pokeball_pos[1] + (my-catch_pokeball_pos[1]) * t_arc/20 + 0.03*t_arc*t_arc)
                pygame.draw.circle(screen, (255,255,0), (px, py), 3)

        # Pokéball throw animation
        pokeball_angle = 0
        pokeball_scale = 1.0
        if catch_animating:
            catch_anim_time += 1
            catch_pokeball_pos[0] += catch_pokeball_vel[0]
            catch_pokeball_pos[1] += catch_pokeball_vel[1]
            catch_pokeball_vel[1] += 0.5  # less gravity for easier aim
            pokeball_angle = catch_anim_time * 12
            pokeball_scale = 1.0 + 0.2*math.sin(catch_anim_time/3)
            # Check collision with any Pokémon
            for p in pokemon_list:
                if (abs(catch_pokeball_pos[0] - p['x']) < 40 and abs(catch_pokeball_pos[1] - p['y']) < 40):
                    catch_result = random.choice([True, False, True])  # slightly higher catch chance
                    catch_animating = False
                    catch_anim_time = 0
                    catch_target_idx = p['idx']
                    catch_target_p = p
                    break
            # Out of bounds = miss
            if catch_pokeball_pos[1] > y or catch_pokeball_pos[0] < 0 or catch_pokeball_pos[0] > x:
                catch_result = False
                catch_animating = False
                catch_anim_time = 0

        # Only show the target Pokémon (the closest to center)
        if catch_animating or catch_dragging:
            # Find closest Pokémon to center
            target_p = min(pokemon_list, key=lambda p: (p['x']-x//2)**2 + (p['y']-y//2)**2)
        elif 'catch_target_p' in locals():
            target_p = catch_target_p
        else:
            target_p = min(pokemon_list, key=lambda p: (p['x']-x//2)**2 + (p['y']-y//2)**2)

        poke_img = target_p['frame'].copy()
        poke_wiggle = 0
        poke_flash = False
        if catch_result is not None:
            poke_wiggle = int(8 * math.sin(catch_anim_time*2))
            poke_flash = catch_anim_time % 8 < 4
        if poke_flash:
            poke_img.fill((255,255,255), special_flags=pygame.BLEND_RGB_ADD)
        screen.blit(poke_img, (target_p['x'] - 45 + poke_wiggle, target_p['y'] - 50))

        # Draw Pokéball (scale/rotate)
        ball_img = pygame.transform.rotozoom(pokeball, pokeball_angle, pokeball_scale)
        if not catch_animating and not catch_dragging:
            screen.blit(ball_img, (catch_pokeball_pos[0] - ball_img.get_width()//2, catch_pokeball_pos[1] - ball_img.get_height()//2))
        elif catch_dragging:
            mx, my = mouse.get_pos()
            screen.blit(ball_img, (mx - ball_img.get_width()//2, my - ball_img.get_height()//2))
        else:
            screen.blit(ball_img, (catch_pokeball_pos[0] - ball_img.get_width()//2, catch_pokeball_pos[1] - ball_img.get_height()//2))

        # Result animation
        if catch_result is not None:
            if catch_result:
                # Success: stars/confetti
                for s in range(30):
                    angle = s * 12 + t*120
                    dist = 60 + 20*math.sin(t*2+s)
                    sx = int(target_p['x'] + dist * math.cos(angle))
                    sy = int(target_p['y'] + dist * math.sin(angle))
                    color = (255,255,100+int(100*math.sin(angle)))
                    pygame.draw.circle(screen, color, (sx, sy), 4)
                font = pygame.font.SysFont("couriernew", 48, bold=True)
                text = font.render("Caught!", True, (255, 255, 100))
                screen.blit(text, (x//2 - text.get_width()//2, 80))
                if catch_anim_time > 60:
                    pokemon_caught = True
                    pokedex_unlocked = True
                    caught_time = pygame.time.get_ticks()
                    # Add caught Pokémon to index
                    caught_pokemon.add(target_p['idx'])
                    # Remove caught Pokémon from field
                    pokemon_list.remove(target_p)
                    # Award 2 extra pokeballs
                    pokeball_count += 2
                    # Clear window and return to main
                    screen.fill((0,0,0))
                    pygame.display.flip()
                    pygame.time.wait(500)
                    catch_scene = False
                    catch_result = None
            else:
                # Failure: shake and red X
                shake = int(10 * math.sin(t*20))
                font = pygame.font.SysFont("couriernew", 48, bold=True)
                text = font.render("Missed!", True, (255, 100, 100))
                screen.blit(text, (x//2 - text.get_width()//2 + shake, 80))
                if catch_anim_time > 60:
                    catch_scene = False
                    catch_result = None
        pygame.display.flip()
        continue

    #map screen
    if pokedex_open == False:
        dt = clock.tick_busy_loop(60)
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                #TAB - open pokedex
                if event.key == pygame.K_TAB and pokedex_unlocked == True:
                    pokedex_open = True
                #SPACE
                #trigger catch mini-game if close enough to any Pokémon
                if event.key == pygame.K_SPACE and not pokeball_thrown and not pokemon_caught and pokeball_count > 0:
                    for p in pokemon_list:
                        if (p['x'] - 100 < trainer_x < p['x'] + 100) and (p['y'] - 100 < trainer_y < p['y'] + 100):
                            catch_scene = True
                            pokeball_count -= 1
                            catch_pokeball_pos = [x//2, y - 60]
                            catch_pokeball_vel = [0, 0]
                            catch_animating = False
                            catch_dragging = False
                            catch_result = None
                            catch_anim_time = 0
                            break
                    continue
                if event.key == pygame.K_SPACE and pokeball_count <= 0:
                    print('not enogh pokeballs')
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    clicked = True
                    mx, my = mouse.get_pos()
        keys = pygame.key.get_pressed()
        moving = False
        #move all Pokémon randomly in grass area
        for p in pokemon_list:
            if p['moving']:
                p['x'] += p['dx'] * dt
                p['y'] += p['dy'] * dt
                # bounce off grass boundaries
                if p['x'] < 120 or p['x'] > x-120:
                    p['dx'] *= -1
                if p['y'] < 120 or p['y'] > y-120:
                    p['dy'] *= -1
                # random direction change
                if random.random() < 0.01:
                    angle = random.uniform(0, 2*math.pi)
                    speed = random.uniform(0.1,0.3)
                    p['dx'] = math.cos(angle)*speed
                    p['dy'] = math.sin(angle)*speed
        #resolve the throw after 1.5s — decide if caught or not
        if pokeball_thrown and pygame.time.get_ticks() - throw_start > 1500:
            pokeball_thrown = False
            pokemon_caught = random.choice([True, False])   #50/50 catch chance
        #movement block — locked while pokeball is catching pokemon
        if not pokeball_thrown:
            if keys[pygame.K_LEFT] and trainer_x > 0:
                trainer_x -= trainer_speed * dt
                facing = 'left'
                moving = True
            if keys[pygame.K_RIGHT] and trainer_x < x - trainer_width:
                trainer_x += trainer_speed * dt
                facing = 'right'
                moving = True
            if keys[pygame.K_UP] and trainer_y > 0:
                trainer_y -= trainer_speed * dt
                facing = 'up'
                moving = True
            if keys[pygame.K_DOWN] and trainer_y < y - trainer_height:
                trainer_y += trainer_speed * dt
                facing = 'down'
                moving = True
        #animation block
        if moving:
            frame_index = (frame_index + animation_speed * dt) % 4
        else:
            frame_index = 0.0
        screen.fill((40, 80, 40))
        #upon mouse click...
        if clicked:
            print(mx, my)
            clicked = False
        #print the map background
        for row in range(2):
            for col in range(2):
                screen.blit(background, (col * tile_width, row * tile_height))
        #print the trainer — round coords to avoid jitter
        trainer_frame = animations[facing][int(frame_index)]
        screen.blit(
            trainer_frame,
            (round(trainer_x),
             round(trainer_y))
        )
        # Draw all Pokémon
        for p in pokemon_list:
            screen.blit(p['frame'], (p['x'], p['y']))
        if pokemon_caught:
            if caught_time == 0:
                caught_time = pygame.time.get_ticks()      #starts timer for when to fade out 'caught' notification
            pokedex_unlocked = True
            elapsed = pygame.time.get_ticks() - caught_time      #time elapsed where 'caught' is on screen
            alpha = max(0, 300 - elapsed // 8)           #turns time elapsed into a computable transparency to be used on caught text and the pill behind it
            font = pygame.font.SysFont("couriernew", 25, bold=True)
            text = font.render("Caught!", True, (255, 255, 100))
            caught_pill = pygame.Surface((text.get_width() + 20, text.get_height() + 10), pygame.SRCALPHA)
            caught_pill.fill((0, 0, 0, 150))
            text.set_alpha(alpha)               #sets the transparency to alpha
            caught_pill.set_alpha(alpha)
            screen.blit(caught_pill, (400 - caught_pill.get_width() // 2, 20))
            screen.blit(text, (400 - text.get_width() // 2, 25))
            if alpha == 0:
                pokemon_caught = False
        #SPACE hint (that says [space] to throw
        font = pygame.font.SysFont("couriernew",19, bold=True)        #font of hint
        hint = font.render("[SPACE] catch", True, (255,255,255))
        #background pill of hint
        pill = pygame.Surface((hint.get_width() + 2, hint.get_height() + 2), pygame.SRCALPHA)    #sets up the background pill (SCRALPHA makes it transparent)
        pill.fill((0, 0, 0, 150))     #colour of pill
        screen.blit(pill, (x - 150, y - 70))    #pill placement
        screen.blit(hint, (x - 150, y - 70))
        # TAB hint (that says [space] to throw
        if pokedex_unlocked:
            tab_font = pygame.font.SysFont("couriernew", 15, bold=True)  # font of hint
            tab_hint = font.render("[TAB] pokédex", True, (255, 255, 255))
            tab_pill = pygame.Surface((tab_hint.get_width() + 2, tab_hint.get_height() + 2),
                                  pygame.SRCALPHA)  # sets up the background pill (SCRALPHA makes it transparent)
            tab_pill.fill((0, 0, 0, 150))  # colour of pill
            screen.blit(tab_pill, (x - 150, y - 40))  # pill placement
            screen.blit(tab_hint, (x - 150, y - 40))
        #pokeball counter top left
        pokeball_font = pygame.font.SysFont('couriernew',20, bold=True)
        pokeball_counter = font.render(f'{pokeball_count}', True, (255, 255, 255))
        if pokeball_count == 0:
            pokeball_counter = font.render(f'{pokeball_count}', True, (255, 0,0))                  #counter goes red if 0 pokeballs
        pokeball_pill = pygame.Surface((60, 20), pygame.SRCALPHA)         #pokeball counter pill dimensions
        pokeball_pill.fill((0,0,0, 150))                                       #pokemon colour
        screen.blit(pokeball_pill, (5,10))
        pokeball = pygame.transform.scale(pokeball, (30,30))          #enlarge pokeball a bit
        screen.blit(pokeball,(4,2))
        screen.blit(pokeball_counter, (35, 10))
        pokeball = pygame.transform.scale(pokeball, (pokeball_width, pokeball_height))     #change pokeball dimensions back
    # pokdex screen
    if pokedex_open == True:
        dt = clock.tick_busy_loop(60)  # more precise than tick() — burns CPU but eliminates timer jitter

        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

                # TAB - close pokedex
                if event.key == pygame.K_TAB:
                    pokedex_open = False

            # mouse wheel scrolling
            if event.type == pygame.MOUSEWHEEL and (scroll_y + event.y * 20 <= 0 or scroll_y + event.y * 20 > 100):
                scroll_y += event.y * 20  # change scroll amount

        screen.fill((100, 30, 30))

        # draw each row of pokemon
        incrementer = 0
        for i in range(len(pokemon_pool)):
            pokemon_image = pokemon_pool[i]
            pokemon_image = pygame.transform.scale(pokemon_image, (250, 250))
            font = pygame.font.SysFont("couriernew", 40, bold=True)
            incrementer = (incrementer +1)%3
            x_pos = incrementer * 275
            if incrementer == 1:
                y_pos = i * 100 + scroll_y  # position of each letter (moves with scroll)
            # Show real image and name if caught, else shadow and ?
            if i in caught_pokemon:
                screen.blit(pokemon_image, (x_pos, y_pos))
                name = pokemon_names[i] if i < len(pokemon_names) else f"Pokemon {i+1}"
                pokemon_name = font.render(name, True, (255,255,255))
            else:
                shadow = pokemon_image.copy()
                shadow.fill((0, 0, 0), special_flags=pygame.BLEND_RGB_MULT)
                screen.blit(shadow, (x_pos, y_pos))
                pokemon_name = font.render("?", True, (80,80,80))
            screen.blit(pokemon_name, (x_pos + 115 , y_pos + 250))

        pygame.display.update()
        clock.tick(60)


    pygame.display.flip()

#todo 1. get catching working ✔️
#todo 2. add in a caught message (temporary banner) ✔️
#todo 3. add in a pokeball counter ✔️
#todo 4. make the 'caught' banner fade away ✔️
#todo 5. add in multiple spawning pokemon ✔️
#todo 6. make it so you can run over where the caught pokemon was again ✔️
#todo 7. add in a pokedex button ✔️
#todo 8. add in a notification explaining the pokedex after first pokemon catch
#todo 9. add stars around pokemon and catch animation (wiggle)
#todo 10. add in pokedex (with shadows for undiscovered pokemon) and names of pokemon too (scrollable and sorrtred into generations) i.e gen 1 bulbasaur charizard squirtle, gen 2...
#todo 11. add in opening screen (fades in) and a login (which tracks pokedex)