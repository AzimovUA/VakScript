# TODO: GET LIMIT FPS to avoid black screen
# TODO: Fix Limit track
# TODO: Add gold tracker

# verified context and no warnings.
import requests
import ssl

# ext
from pyMeow import open_process, get_module, get_color, load_font, get_monitor_refresh_rate

# from pyMeow import overlay_init, overlay_loop, overlay_close, begin_drawing, end_drawing
# from pyMeow import draw_line, draw_circle, draw_font, gui_progress_bar, gui_text_box

from pyMeow import r_uint64

# from win32api import GetSystemMetrics
from gc import collect as del_mem
from time import sleep
import win32gui
import win32con
import dearpygui.dearpygui as dpg
# import win32api
# import cv2
# from mss import mss
# import numpy as np
import win32api
# import imutils
import keyboard
import ctypes
from ctypes import c_int
import time

# own
from data import Data, Offsets
from entities import EntityDrawings, ReadAttributes, distance
from world_to_screen import World
from settings import jsonGetter

requests.packages.urllib3.disable_warnings()
ssl._create_default_https_context = ssl._create_unverified_context


class MARGINS(ctypes.Structure):
    _fields_ = [("cxLeftWidth", c_int),
                ("cxRightWidth", c_int),
                ("cyTopHeight", c_int),
                ("cyBottomHeight", c_int)
                ]


'''def show_fov(sender, data):
    global circle
    if data:
        sl_value = dpg.get_value(slider1)
        circle = dpg.draw_circle((width / 2, height / 2), sl_value, color=(255, 255, 0, 255), parent="Viewport_back",
                                 thickness=3)
    if not data:
        dpg.delete_item(circle)'''


def drawings(terminate, settings, champion_pointers, on_window):
    yellow = get_color('yellow')
    red = get_color('red')
    cyan = get_color('cyan')
    gold = get_color('gold')

    def draw_enemy_line(entity, own_pos, width, height):
        if entity.alive and entity.targetable and entity.visible:
            pos = world_to_screen(get_view_proj_matrix(), entity.x, entity.z, entity.y)
            if pos:
                x, y = pos[0], pos[1]
                if (x < 0 or x > width or y < 0 or y > height) and distance(player, entity) <= 3000:
                    dpg.draw_line((own_pos[0], own_pos[1]), (x, y), color=(255, 0, 0, 255), thickness=5, parent="Viewport_back")
                else:
                    dpg.draw_line((own_pos[0], own_pos[1]), (x, y), color=(0, 255, 255, 255), thickness=5, parent="Viewport_back")
                    dpg.draw_circle((x, y), 45, color=(0, 255, 255, 255), thickness=3, parent="Viewport_back")


    while not terminate.value:
        if on_window.value:
            del_mem()
            try:
                process = open_process(process=Data.game_name_executable)
                base_address = get_module(process, Data.game_name_executable)['base']
                local = r_uint64(process, base_address + Offsets.local_player)
                attr = ReadAttributes(process, base_address)

                width = win32api.GetSystemMetrics(0)
                height = win32api.GetSystemMetrics(1)

                dwm = ctypes.windll.dwmapi
                dpg.create_context()
                dpg.create_viewport(title='overlay', always_on_top=True, decorated=False,
                                    clear_color=[0.0, 0.0, 0.0, 0.0])
                dpg.set_viewport_always_top(True)
                dpg.create_context()
                dpg.setup_dearpygui()

                dpg.add_viewport_drawlist(front=False, tag="Viewport_back")

                dpg.show_viewport()
                dpg.toggle_viewport_fullscreen()

                hwnd = win32gui.FindWindow(None, "overlay")
                margins = MARGINS(-1, -1, -1, -1)
                dwm.DwmExtendFrameIntoClientArea(hwnd, margins)

                # Limits FPS for drawings with refresh rate of monitor
                dpg.set_viewport_vsync(True)
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                                       win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)

                with dpg.font_registry():
                    health_font = dpg.add_font(Data.font_file_name, 15, default_font=True)

                # game variables
                world = World(process, base_address, width, height)
                entity = EntityDrawings(process, base_address, width, height)

                can_track = settings['position_tracker']
                can_focus = settings['show_focused']
                can_healths = settings['show_healths']
                can_track_spells = settings['spell_tracker']
                limited_draw = settings['screen_track']
                target_prio = jsonGetter().get_data('orbwalk_prio')
                potato_pc = jsonGetter().get_data('ppc')

                target_prio_mode = {'Less Basic Attacks': entity.select_by_health,
                                    'Most Damage': entity.select_by_damage,
                                    'Nearest Enemy': entity.select_by_distance}

                select_target = target_prio_mode.get(target_prio, entity.select_by_health)
                read_player = attr.read_player
                read_enemy = attr.read_enemy
                read_spells = attr.read_spells
                spells_keys = attr.spells_keys
                world_to_screen = world.world_to_screen
                world_to_screen_limited = world.world_to_screen_limited
                get_view_proj_matrix = world.get_view_proj_matrix

                fps = 60
                if potato_pc:
                    fps = 30
                if limited_draw:
                    world_to_screen = world.world_to_screen_limited

            except:
                print('Error on drawings.py')
                continue

            else:
                while dpg.is_dearpygui_running():
                    try:
                        dpg.render_dearpygui_frame()
                        entities = [read_enemy(pointer) for pointer in champion_pointers]
                        player = read_player(local)
                        own_pos = world_to_screen_limited(get_view_proj_matrix(), player.x, player.z, player.y)

                        # clear drawings
                        try:
                            dpg.delete_item("Viewport_back")
                        except:
                            pass
                        dpg.add_viewport_drawlist(front=False, tag="Viewport_back")

                        if not on_window.value:
                            break

                        if own_pos:
                            dpg.draw_circle((own_pos[0], own_pos[1]), 5, color=(255, 255, 0, 255),
                                            parent="Viewport_back", fill=(255, 255, 0, 255))

                        if can_track:
                            own_pos = world_to_screen(get_view_proj_matrix(), player.x, player.z, player.y)
                            for entity in entities:
                                draw_enemy_line(entity, own_pos, width, height)

                        if can_focus:
                            target = select_target(player, entities)
                            if target:
                                pos = world_to_screen_limited(get_view_proj_matrix(), target.x, target.z, target.y)
                                if pos and own_pos:
                                    dpg.draw_circle((pos[0], pos[1]), 45, thickness=5, color=(255, 255, 0, 255), parent="Viewport_back")

                        if can_healths:
                            ypos = height
                            for entity in entities:
                                ypos -= 30
                                text = dpg.draw_text((5, ypos), entity.name, color=(255, 255, 0, 255), size=16, parent="Viewport_back")
                                hp_percent = entity.health / entity.max_health
                                dpg.draw_rectangle((100, ypos), (200, ypos + 15), color=(0, 0, 0, 255), thickness=2, parent="Viewport_back")
                                dpg.draw_rectangle((100, ypos), (100 + (100 * hp_percent), ypos + 15), color=(0, 255, 0, 255), fill=(0, 255, 0, 255), parent="Viewport_back")
                                # dpg.add_progress_bar(parent="Viewport_back", pos=(100, ypos), width=100, height=15,
                                #                      default_value=hp_percent)

                    except:
                        pass
        sleep(.1)
    dpg.destroy_context()
