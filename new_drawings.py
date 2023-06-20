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
import ctypes
from ctypes import c_int, windll

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


def drawings(terminate, settings, champion_pointers, on_window):
    def draw_enemy_line(entity, i, own_pos, width, height, track_draw):
        if entity.alive and entity.targetable and entity.visible:
            pos = world_to_screen(get_view_proj_matrix(), entity.x, entity.z, entity.y)
            if pos:
                x, y = pos[0], pos[1]
                if (x < 0 or x > width or y < 0 or y > height) and distance(player, entity) <= 3000:
                    dpg.configure_item(track_draw[i][0], p1=(own_pos[0], own_pos[1]), p2=(x, y))
                else:
                    dpg.configure_item(track_draw[i][1], p1=(own_pos[0], own_pos[1]), p2=(x, y))
                    dpg.configure_item(track_draw[i][2], center=(x, y))
                dpg.show_item(f'track_draw_group_{i}')

    while not terminate.value:
        del_mem()
        try:
            process = open_process(process=Data.game_name_executable)
            base_address = get_module(process, Data.game_name_executable)['base']
            local = r_uint64(process, base_address + Offsets.local_player)
            attr = ReadAttributes(process, base_address)

            dpg.create_context()
            dpg.create_viewport(title='overlay', always_on_top=True, decorated=False,
                                clear_color=(0.0, 0.0, 0.0, 0.0),
                                vsync=True)
            dpg.set_viewport_always_top(True)
            dpg.setup_dearpygui()

            dpg.add_viewport_drawlist(front=False, tag="Viewport_back")

            dpg.show_viewport()
            dpg.toggle_viewport_fullscreen()

            width = win32api.GetSystemMetrics(0)
            height = win32api.GetSystemMetrics(1)

            hwnd = win32gui.FindWindow(None, "overlay")
            margins = MARGINS(-1, -1, -1, -1)
            windll.dwmapi.DwmExtendFrameIntoClientArea(hwnd, margins)

            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                                   win32gui.GetWindowLong(hwnd,
                                   win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)

            with dpg.font_registry():
                dpg.add_font(Data.font_file_name, 15, default_font=True)

            # game variables
            world = World(process, base_address, width, height)
            entity = EntityDrawings(process, base_address, width, height)

            can_track = settings['position_tracker']
            can_focus = settings['show_focused']
            can_healths = settings['show_healths']
            can_track_spells = settings['spell_tracker']
            limited_draw = settings['screen_track']
            target_prio = jsonGetter().get_data('orbwalk_prio')

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

            if limited_draw:
                world_to_screen = world.world_to_screen_limited

            # drawings
            own_pos_draw = dpg.draw_circle((0, 0), 5, color=(255, 255, 0, 255),
                                           parent="Viewport_back", fill=(255, 255, 0, 255))

            focus_draw = dpg.draw_circle((0, 0), 45, thickness=8, color=(255, 255, 0, 255),
                                         parent="Viewport_back")

            track_draw, healths_draw, spells_draw = [], [], []
            for i in range(len(champion_pointers)):
                dpg.add_draw_layer(parent="Viewport_back", tag=f"track_draw_group_{i}")
                track_draw_ids = [dpg.draw_line((0, 0), (1, 1), color=(255, 0, 0, 255),
                                                thickness=1, parent=f"track_draw_group_{i}"),
                                  dpg.draw_line((0, 0), (1, 1), color=(0, 255, 255, 255),
                                                thickness=1, parent=f"track_draw_group_{i}"),
                                  dpg.draw_circle((0, 0), 45, color=(0, 255, 255, 255),
                                                  thickness=2, parent=f"track_draw_group_{i}")]

                dpg.add_draw_layer(parent="Viewport_back", tag=f"healths_draw_group_{i}")
                healths_draw_ids = [dpg.draw_text((5, 0), "", color=(255, 255, 0, 255),
                                                  size=16, parent=f"healths_draw_group_{i}"),
                                    dpg.draw_rectangle((0, 0), (1, 1), color=(0, 0, 0, 255),
                                                       thickness=2, parent=f"healths_draw_group_{i}"),
                                    dpg.draw_rectangle((0, 0), (1, 1), color=(0, 255, 0, 255),
                                                       fill=(0, 255, 0, 255), parent=f"healths_draw_group_{i}")]

                dpg.add_draw_layer(parent="Viewport_back", tag=f"spells_draw_group_{i}")
                spells_draw_ids = [
                    dpg.draw_rectangle((0, 0), (1, 1), color=(255, 255, 0, 255), parent=f"spells_draw_group_{i}"),
                    dpg.draw_rectangle((0, 0), (1, 1), color=(255, 255, 0, 255), parent=f"spells_draw_group_{i}"),
                    dpg.draw_rectangle((0, 0), (1, 1), color=(255, 255, 0, 255), parent=f"spells_draw_group_{i}"),
                    dpg.draw_rectangle((0, 0), (1, 1), color=(255, 255, 0, 255), parent=f"spells_draw_group_{i}"),
                    dpg.draw_text((0, 0), "", color=(255, 255, 0, 255), size=18, parent=f"spells_draw_group_{i}"),
                    dpg.draw_text((0, 0), "", color=(255, 255, 0, 255), size=18, parent=f"spells_draw_group_{i}"),
                    dpg.draw_text((0, 0), "", color=(255, 255, 0, 255), size=18, parent=f"spells_draw_group_{i}"),
                    dpg.draw_text((0, 0), "", color=(255, 255, 0, 255), size=18, parent=f"spells_draw_group_{i}"),
                    dpg.draw_text((0, 0), "", color=(0, 255, 255, 255), size=15, parent=f"spells_draw_group_{i}"),
                    dpg.draw_text((0, 0), "", color=(0, 255, 255, 255), size=15, parent=f"spells_draw_group_{i}"),
                    dpg.draw_text((0, 0), "", color=(0, 255, 255, 255), size=15, parent=f"spells_draw_group_{i}"),
                    dpg.draw_text((0, 0), "", color=(0, 255, 255, 255), size=15, parent=f"spells_draw_group_{i}"),
                    dpg.draw_text((0, 0), "", color=(255, 255, 0, 255), size=15, parent=f"spells_draw_group_{i}"),
                    dpg.draw_rectangle((0, 0), (1, 1), color=(255, 255, 0, 255),
                                       parent=f"spells_draw_group_{i}"),
                    dpg.draw_rectangle((0, 0), (1, 1), color=(255, 255, 0, 255),
                                       parent=f"spells_draw_group_{i}"),
                    dpg.draw_rectangle((0, 0), (1, 1), color=(255, 255, 0, 255),
                                       parent=f"spells_draw_group_{i}"),
                    dpg.draw_rectangle((0, 0), (1, 1), color=(255, 255, 0, 255),
                                       parent=f"spells_draw_group_{i}"),
                    dpg.draw_text((0, 0), "", color=(255, 255, 0, 255), size=15, parent=f"spells_draw_group_{i}"),
                    dpg.draw_text((0, 0), "", color=(255, 255, 0, 255), size=15, parent=f"spells_draw_group_{i}"),
                    dpg.draw_text((0, 0), "", color=(255, 255, 0, 255), size=15, parent=f"spells_draw_group_{i}"),
                    dpg.draw_text((0, 0), "", color=(255, 255, 0, 255), size=15, parent=f"spells_draw_group_{i}"), ]

                track_draw.append(track_draw_ids.copy())
                healths_draw.append(healths_draw_ids.copy())
                spells_draw.append(spells_draw_ids.copy())

        except Exception as error:
            print('Error on drawings.py', error)
            continue

        else:
            while True:
                if terminate.value:
                    break
                elif on_window.value:
                    closed = False
                    while dpg.is_dearpygui_running():
                        try:
                            dpg.render_dearpygui_frame()
                            entities = [read_enemy(pointer) for pointer in champion_pointers]
                            player = read_player(local)
                            own_pos = world_to_screen_limited(get_view_proj_matrix(), player.x, player.z, player.y)
                            dpg.hide_item(own_pos_draw)
                            dpg.hide_item(focus_draw)

                            for i in range(len(champion_pointers)):
                                dpg.hide_item(f"track_draw_group_{i}")
                                dpg.hide_item(f"healths_draw_group_{i}")
                                dpg.hide_item(f"spells_draw_group_{i}")

                            if not on_window.value:
                                if closed:
                                    break
                                closed = True
                                dpg.render_dearpygui_frame()
                                continue

                            if own_pos:
                                dpg.configure_item(own_pos_draw, center=(own_pos[0], own_pos[1]))
                                dpg.show_item(own_pos_draw)

                            if can_track:
                                own_pos = world_to_screen(get_view_proj_matrix(), player.x, player.z, player.y)
                                if own_pos:
                                    for i, entity in enumerate(entities):
                                        draw_enemy_line(entity, i, own_pos, width, height, track_draw)

                            if can_focus:
                                target = select_target(player, entities)
                                if target:
                                    pos = world_to_screen_limited(get_view_proj_matrix(), target.x, target.z, target.y)
                                    if pos and own_pos:
                                        dpg.configure_item(focus_draw, center=(pos[0], pos[1]))
                                        dpg.show_item(focus_draw)

                            if can_healths:
                                ypos = height
                                for i, entity in enumerate(entities):
                                    ypos -= 30
                                    dpg.configure_item(healths_draw[i][0], pos=(5, ypos), text=entity.name)
                                    hp_percent = entity.health / entity.max_health
                                    dpg.configure_item(healths_draw[i][1], pmin=(100, ypos), pmax=(200, ypos + 15))
                                    dpg.configure_item(healths_draw[i][2], pmin=(100, ypos),
                                                       pmax=(100 + (100 * hp_percent), ypos + 15))
                                    dpg.show_item(f"healths_draw_group_{i}")

                            if can_track_spells:
                                spells = [read_spells(pointer) for pointer in champion_pointers]
                                ypos = height
                                for i, entity in enumerate(entities):
                                    ypos -= 30
                                    pos = world_to_screen_limited(get_view_proj_matrix(), entity.x, entity.z, entity.y)

                                    if pos:
                                        x_space = 0
                                        for n, slot in enumerate(spells_keys[:-2]):
                                            dpg.configure_item(spells_draw[i][n],
                                                               pmin=(pos[0] - 60 + x_space, pos[1] - 125),
                                                               pmax=(pos[0] - 25 + x_space, pos[1] - 100))
                                            dpg.configure_item(spells_draw[i][4 + n],
                                                               pos=(pos[0] - 50 + x_space, pos[1] - 120),
                                                               text=str(spells[i][slot][1]))
                                            dpg.configure_item(spells_draw[i][8 + n],
                                                               pos=(pos[0] - 50 + x_space, pos[1] - 95),
                                                               text=str(spells[i][slot][0]))
                                            x_space += 35
                                        x_space = 100
                                        if can_healths:
                                            x_space = 210

                                        for n, slot in enumerate(spells_keys[-2:]):
                                            if not can_healths:
                                                dpg.configure_item(spells_draw[i][12], pos=(5, ypos), text=entity.name)
                                            dpg.configure_item(spells_draw[i][13 + n], pmin=(x_space, ypos - 5),
                                                               pmax=(x_space + 35, ypos + 20))
                                            dpg.configure_item(spells_draw[i][17 + n], pos=(x_space + 3, ypos),
                                                               text=str(spells[i][slot][0]))
                                            x_space += 40
                                        dpg.show_item(f"spells_draw_group_{i}")

                        except Exception as error:
                            print('Error on drawings.py: dpg.is_dearpygui_running():', error)

                sleep(0.25)
    sleep(.1)
