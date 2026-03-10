#libraries
import sys
from pygame import mouse
import pygame

#variables
x, y =800, 700
tile_width = x/2
tile_height = y/2
clicked = False
trainer_x, trainer_y = 500, 300            #trainer coordinates (initial)
trainer_speed = 0.3                        #walk speed of trainer
trainer_width, trainer_height = 70,90    #trainer proportions
frame_width, frame_height = 840/4, 595/4
facing = 'down'
animation_speed = 0.15                       #speed of animation

frame_index = 0

#initialisation
pygame.init()
pygame.display.set_caption('Pokemon game')    #make window
screen = pygame.display.set_mode((x, y))      #dimensions
font = pygame.font.SysFont(name="Arcade Classic", size=90)  #font of text

#load images into a variable 
background = pygame.image.load("maps/grassy.jpg")                  #map
background = pygame.transform.scale(background, (tile_width, tile_height))   #scale
trainer_sheet = pygame.image.load("images/trainer_sheet.png").convert_alpha()

animations = {'down':[],'left':[],'right':[],'up':[]}
direction_rows = {0:'down', 1:'left', 2:'right', 3:'up'}

for row in range(4):                     #iterates through each rows
    direction = direction_rows[row]      #iterates through each frame within that row
    for col in range(4): 
        frame = trainer_sheet.subsurface(pygame.Rect( col*frame_width, row*frame_height, frame_width, frame_height))
        animations[direction].append(frame)   #to now get it in the format ['down'][0][1][2][3]


#event loop
while True:
    keys = pygame.key.get_pressed()  # get all pressed keys
    moving = False
    
    #movement block
    if keys[pygame.K_LEFT] and trainer_x > 0:  #is key pressed and is sprite on map
        trainer_x -= trainer_speed             #moves coordinate
        facing = 'left'                        #sets direction
        moving = True                          #triggers animation
        
    if keys[pygame.K_RIGHT] and trainer_x < y + trainer_width/2:
        trainer_x += trainer_speed
        facing = 'right'
        moving = True
        
    if keys[pygame.K_UP] and trainer_y > 0:
        trainer_y -= trainer_speed
        facing = 'up'
        moving = True
        
    if keys[pygame.K_DOWN] and trainer_y < y - trainer_height:
        trainer_y += trainer_speed
        facing = 'down'
        moving = True
        
    #animation block
    if moving:
        frame_index = (frame_index + animation_speed) % 4
    else:
        frame_index = 0
        
        
        
    for event in pygame.event.get():                #check if any keys are pressed
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                clicked = True
                mx, my = mouse.get_pos()


    screen.fill((40, 80, 40))  #background colour
    
    #upon mouse click...
    if clicked:
        print(mx, my)
        clicked = False


    #print the map background
    for row in range(2):
        for col in range(2):
            screen.blit(background,(col*tile_width, row*tile_height))   
    
    #print the sprite
    frame = animations[facing][int(frame_index)]                
    frame = pygame.transform.scale(frame, (trainer_width, trainer_height))
    screen.blit(frame, (trainer_x, trainer_y))


    pygame.display.flip()