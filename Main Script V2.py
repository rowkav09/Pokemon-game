#libraries
import sys
from pygame import mouse
import pygame

#region Variables
x, y = 800, 700
tile_width = x/2
tile_height = y/2
clicked = False
trainer_x, trainer_y = 500.0, 300.0       #floats for smooth sub-pixel movement
trainer_speed = 0.3                        #walk speed (pixels per ms)
trainer_width, trainer_height = 70, 90    #trainer proportions
trainer_frame_width, trainer_frame_height = 121, 126      #actual frame size (sprites don't start at 0,0)
trainer_frame_offset_x, trainer_frame_offset_y = 177, 45  #black padding offset in sprite sheet
facing = 'down'
animation_speed = 0.005                    #animation speed (frames per ms)
frame_index = 0.0                          #initialise frame index
# endregion

#pokemon_frame_offset

#initialisation
pygame.init()
pygame.display.set_caption('Pokemon game')
screen = pygame.display.set_mode((x, y))
font = pygame.font.SysFont(name="Arcade Classic", size=90)
clock = pygame.time.Clock()               #clock for delta time
    
#load images
    #map
background = pygame.image.load("maps/grassy.jpg")
background = pygame.transform.scale(background, (tile_width, tile_height))
    #sprite
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
    #pokemon
    #TODO make random pokemon pop up in the centre of the screen
pokemon_sheet = pygame.image.load("images/3d_starter_sheet.png").convert_alpha()
pokemon_pool = []
for row in range(4):
    for col in range(4):
        pokemon_frame = pokemon_sheet.subsurface(pygame.Rect(
            pokemon_frame_offset_x + col * frame_width,
            pokemon_frame_offset_y + row * frame_height,
            frame_width, frame_height
        ))
        pokemon_frame = pygame.transform.scale(frame, (pokemon_width, pokemon_height))  #pre-scale once
        .append(pokemon_frame)
        
#event loop
while True:
    dt = clock.tick_busy_loop(60)          #more precise than tick() — burns CPU but eliminates timer jitter

    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                clicked = True
                mx, my = mouse.get_pos()

    keys = pygame.key.get_pressed()
    moving = False

    #movement block — multiply by dt so speed is consistent regardless of framerate
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

    #print the sprite — round coords to avoid  jitter
    frame = animations[facing][int(frame_index)]
    screen.blit(frame, (round(trainer_x), round(trainer_y)))

    pygame.display.flip()