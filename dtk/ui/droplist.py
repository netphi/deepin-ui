#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2011 ~ 2012 Deepin, Inc.
#               2011 ~ 2012 Wang Yong
# 
# Author:     Wang Yong <lazycat.manatee@gmail.com>
# Maintainer: Wang Yong <lazycat.manatee@gmail.com>
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from constant import DEFAULT_FONT_SIZE, ALIGN_START, ALIGN_MIDDLE, WIDGET_POS_TOP_LEFT
from draw import draw_vlinear, draw_text
from keymap import get_keyevent_name
from line import HSeparator
from scrolled_window import ScrolledWindow
from theme import ui_theme
import gobject
import gtk
from utils import (is_in_rect, get_content_size, propagate_expose, 
                   get_widget_root_coordinate, get_screen_size, 
                   alpha_color_hex_to_cairo, 
                   cairo_disable_antialias, color_hex_to_cairo)

droplist_grab_window = gtk.Window(gtk.WINDOW_POPUP)
droplist_grab_window.move(0, 0)
droplist_grab_window.set_default_size(0, 0)
droplist_grab_window.show()
droplist_active_item = None
droplist_grab_window_press_flag = False

root_droplists = []

def droplist_grab_window_focus_in():
    droplist_grab_window.grab_add()
    gtk.gdk.pointer_grab(
        droplist_grab_window.window, 
        True,
        gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK | gtk.gdk.ENTER_NOTIFY_MASK | gtk.gdk.LEAVE_NOTIFY_MASK,
        None, None, gtk.gdk.CURRENT_TIME)
    
def droplist_grab_window_focus_out():
    global root_droplists
    
    for root_droplist in root_droplists:
        root_droplist.hide()
    
    root_droplists = []    
    
    gtk.gdk.pointer_ungrab(gtk.gdk.CURRENT_TIME)
    droplist_grab_window.grab_remove()

def is_press_on_droplist_grab_window(window):
    '''Is press on droplist grab window.'''
    for toplevel in gtk.window_list_toplevels():
        if isinstance(window, gtk.Window):
            if window == toplevel:
                return True
        elif isinstance(window, gtk.gdk.Window):
            if window == toplevel.window:
                return True
            
    return False        

def droplist_grab_window_enter_notify(widget, event):
    if event and event.window:
        event_widget = event.window.get_user_data()
        if isinstance(event_widget, DroplistScrolledWindow):
            event_widget.event(event)

def droplist_grab_window_leave_notify(widget, event):
    if event and event.window:
        event_widget = event.window.get_user_data()
        if isinstance(event_widget, DroplistScrolledWindow):
            event_widget.event(event)
            
def droplist_grab_window_scroll_event(widget, event):
    global root_droplists
    
    if event and event.window:
        for droplist in root_droplists:
            droplist.item_scrolled_window.event(event)
            
def droplist_grab_window_key_press(widget, event):
    global root_droplists
    
    if event and event.window:
        for droplist in root_droplists:
            droplist.event(event)

def droplist_grab_window_key_release(widget, event):
    global root_droplists
    
    if event and event.window:
        for droplist in root_droplists:
            droplist.event(event)

def droplist_grab_window_button_release(widget, event):
    global root_droplists
    global droplist_grab_window_press_flag

    droplist_grab_window_press_flag = False
    
    if event and event.window:
        event_widget = event.window.get_user_data()
        if isinstance(event_widget, DroplistScrolledWindow):
            event_widget.event(event)
        else:
            # Make scrolledbar smaller if release out of scrolled_window area.
            for droplist in root_droplists:
                droplist.item_scrolled_window.make_bar_smaller(gtk.ORIENTATION_HORIZONTAL)
                droplist.item_scrolled_window.make_bar_smaller(gtk.ORIENTATION_VERTICAL)
    
def droplist_grab_window_button_press(widget, event):
    global droplist_active_item
    global droplist_grab_window_press_flag

    droplist_grab_window_press_flag = True
    
    if event and event.window:
        event_widget = event.window.get_user_data()
        if is_press_on_droplist_grab_window(event.window):
            droplist_grab_window_focus_out()
        elif isinstance(event_widget, DroplistScrolledWindow):
            event_widget.event(event)
        elif isinstance(event_widget, Droplist):
            droplist_item = event_widget.get_droplist_item_at_coordinate(event.get_root_coords())
            if droplist_item:
                droplist_item.item_box.event(event)
        else:
            event_widget.event(event)
            droplist_grab_window_focus_out()
    
def droplist_grab_window_motion_notify(widget, event):
    global droplist_active_item
    global droplist_grab_window_press_flag
    
    if event and event.window:
        event_widget = event.window.get_user_data()
        if isinstance(event_widget, DroplistScrolledWindow):
            event_widget.event(event)
        elif isinstance(event_widget, Droplist):
            for droplist in root_droplists:
                motion_notify_event = gtk.gdk.Event(gtk.gdk.MOTION_NOTIFY)
                motion_notify_event.window = droplist.item_scrolled_window.vwindow
                motion_notify_event.send_event = True
                motion_notify_event.time = event.time
                motion_notify_event.x = event.x
                motion_notify_event.y = event.y
                motion_notify_event.x_root = event.x_root
                motion_notify_event.y_root = event.y_root
                motion_notify_event.state = event.state
                    
                droplist.item_scrolled_window.event(motion_notify_event)
            
            if not droplist_grab_window_press_flag:
                droplist_item = event_widget.get_droplist_item_at_coordinate(event.get_root_coords())
                if droplist_item and isinstance(droplist_item.item_box, gtk.Button):
                    if droplist_active_item:
                        droplist_active_item.item_box.set_state(gtk.STATE_NORMAL)
                    
                    droplist_item.item_box.set_state(gtk.STATE_PRELIGHT)
                    droplist_active_item = droplist_item
                    
                    enter_notify_event = gtk.gdk.Event(gtk.gdk.ENTER_NOTIFY)
                    enter_notify_event.window = event.window
                    enter_notify_event.time = event.time
                    enter_notify_event.send_event = True
                    enter_notify_event.x_root = event.x_root
                    enter_notify_event.y_root = event.y_root
                    enter_notify_event.x = event.x
                    enter_notify_event.y = event.y
                    enter_notify_event.state = event.state
                    
                    droplist_item.item_box.event(enter_notify_event)
                    
                    droplist_item.item_box.queue_draw()
        else:
            for droplist in root_droplists:
                motion_notify_event = gtk.gdk.Event(gtk.gdk.MOTION_NOTIFY)
                motion_notify_event.window = droplist.item_scrolled_window.vwindow
                motion_notify_event.send_event = True
                motion_notify_event.time = event.time
                motion_notify_event.x = event.x
                motion_notify_event.y = event.y
                motion_notify_event.x_root = event.x_root
                motion_notify_event.y_root = event.y_root
                motion_notify_event.state = event.state
                    
                droplist.item_scrolled_window.event(motion_notify_event)
                
droplist_grab_window.connect("button-press-event", droplist_grab_window_button_press)
droplist_grab_window.connect("button-release-event", droplist_grab_window_button_release)
droplist_grab_window.connect("motion-notify-event", droplist_grab_window_motion_notify)
droplist_grab_window.connect("enter-notify-event", droplist_grab_window_enter_notify)
droplist_grab_window.connect("leave-notify-event", droplist_grab_window_leave_notify)
droplist_grab_window.connect("scroll-event", droplist_grab_window_scroll_event)
droplist_grab_window.connect("key-press-event", droplist_grab_window_key_press)
droplist_grab_window.connect("key-release-event", droplist_grab_window_key_release)
            
class DroplistScrolledWindow(ScrolledWindow):
    '''Droplist scrolled window.'''
	
    def __init__(self, right_space=2, top_bootm_space=3):
        '''Init droplist scrolled window.'''
        ScrolledWindow.__init__(self, right_space, top_bootm_space)
        
gobject.type_register(DroplistScrolledWindow)
                
class Droplist(gtk.Window):
    '''Droplist.'''
    
    __gsignals__ = {
        "item-selected" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (str, gobject.TYPE_PYOBJECT, int,)),
        "key-release" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (str, gobject.TYPE_PYOBJECT, int,)),
    }

    def __init__(self, items, 
                 x_align=ALIGN_START,
                 y_align=ALIGN_START,
                 font_size=DEFAULT_FONT_SIZE, 
                 opacity=1.0, 
                 padding_x=0, 
                 padding_y=0, 
                 item_padding_left=6, 
                 item_padding_right=32,
                 item_padding_y=3,
                 shadow_visible=True,
                 max_width=None):
        '''Init droplist, item format: (item_content, item_value).'''
        # Init.
        gtk.Window.__init__(self, gtk.WINDOW_POPUP)
        self.items = items
        self.set_can_focus(True) # can focus to response key-press signal
        self.add_events(gtk.gdk.ALL_EVENTS_MASK)
        self.set_decorated(False)
        self.set_colormap(gtk.gdk.Screen().get_rgba_colormap())
        global root_droplists
        self.font_size = font_size
        self.x_align = x_align
        self.y_align = y_align
        self.subdroplist = None
        self.root_droplist = None
        self.offset_x = 0       # use for handle extreme situaiton, such as, droplist show at side of screen
        self.offset_y = 0
        self.padding_x = padding_x
        self.padding_y = padding_y
        self.item_padding_left = item_padding_left
        self.item_padding_right = item_padding_right
        self.item_padding_y = item_padding_y
        self.max_width = max_width
        self.item_select_index = 0
        
        # Init droplist window.
        self.set_opacity(opacity)
        self.set_skip_taskbar_hint(True)
        self.set_keep_above(True)
        self.connect_after("show", self.init_droplist)
        
        self.droplist_frame = gtk.Alignment()
        self.droplist_frame.set(0.5, 0.5, 1.0, 1.0)
        self.droplist_frame.set_padding(1, 1, 1, 1)
        
        # Add droplist item.
        self.item_box = gtk.VBox()
        self.item_align = gtk.Alignment()
        self.item_align.set_padding(padding_y, padding_y, padding_x, padding_x)
        self.item_align.add(self.item_box)
        self.item_scrolled_window = DroplistScrolledWindow(0, 0)
        self.add(self.droplist_frame)
        self.droplist_frame.add(self.item_scrolled_window)
        self.item_scrolled_window.add_child(self.item_align)
        self.droplist_items = []
        
        if items:
            for (index, item) in enumerate(items):
                droplist_item = DroplistItem(
                    self,
                    index, item, font_size, 
                    padding_x, padding_y,
                    item_padding_left, item_padding_right, item_padding_y, self.max_width)
                self.droplist_items.append(droplist_item)
                self.item_box.pack_start(droplist_item.item_box, False, False)
                
        self.connect_after("show", self.adjust_droplist_position)        
        self.droplist_frame.connect("expose-event", self.expose_droplist_frame)
        self.item_align.connect("expose-event", self.expose_item_align)
        self.connect("key-press-event", self.droplist_key_press)
        self.connect("key-release-event", self.droplist_key_release)
        
        self.keymap = {
            "Home" : self.select_first_item,
            "End" : self.select_last_item,
            "Page_Up" : self.scroll_page_up,
            "Page_Down" : self.scroll_page_down,
            "Return" : self.press_select_item,
            "Up" : self.select_prev_item,
            "Down" : self.select_next_item,
            "Escape" : self.hide}
        
        self.select_first_item()
        self.grab_focus()
        
    def get_droplist_width(self):
        '''Get droplist width.'''
        item_content_width = max(map(lambda item: get_content_size(item.item[0], self.font_size)[0], 
                                     filter(lambda item: isinstance(item.item_box, gtk.Button), self.droplist_items)))
        if self.max_width != None:
            return self.padding_x * 2 + min(self.max_width,
                                            self.item_padding_left + self.item_padding_right + int(item_content_width))
        else:
            return self.padding_x * 2 + self.item_padding_left + self.item_padding_right + int(item_content_width)
        
    def expose_item_align(self, widget, event):
        '''Expose item align.'''
        # Init.
        cr = widget.window.cairo_create()        
        rect = widget.allocation
        x, y, w, h = rect.x, rect.y, rect.width, rect.height
        
        # Draw background.
        cr.set_source_rgba(*alpha_color_hex_to_cairo(ui_theme.get_alpha_color("droplist_mask").get_color_info()))
        cr.rectangle(x, y, w, h)    
        cr.fill()
        
    def get_first_index(self):
        '''Get first index.'''
        item_indexs = filter(lambda (index, item): isinstance(item.item_box, gtk.Button), enumerate(self.droplist_items))        
        if len(item_indexs) > 0:
            return item_indexs[0][0]
        else:
            return None
        
    def get_last_index(self):
        '''Get last index.'''
        item_indexs = filter(lambda (index, item): isinstance(item.item_box, gtk.Button), enumerate(self.droplist_items))        
        if len(item_indexs) > 0:
            return item_indexs[-1][0]
        else:
            return None
        
    def get_prev_index(self):
        '''Get preview index.'''
        item_indexs = filter(lambda (index, item): isinstance(item.item_box, gtk.Button), enumerate(self.droplist_items))
        if len(item_indexs) > 0:
            index_list = map(lambda (index, item): index, item_indexs)
            if self.item_select_index in index_list:
                current_index = index_list.index(self.item_select_index)
                if current_index > 0:
                    return index_list[current_index - 1]
                else:
                    return self.item_select_index
            else:
                return None
        else:
            return None
        
    def get_next_index(self):
        '''Get next index.'''
        item_indexs = filter(lambda (index, item): isinstance(item.item_box, gtk.Button), enumerate(self.droplist_items))
        if len(item_indexs) > 0:
            index_list = map(lambda (index, item): index, item_indexs)
            if self.item_select_index in index_list:
                current_index = index_list.index(self.item_select_index)
                if current_index < len(index_list) - 1:
                    return index_list[current_index + 1]
                else:
                    return self.item_select_index
            else:
                return None
        else:
            return None
        
    def get_select_item_rect(self, item_index=None):
        '''Get select item rect.'''
        if item_index == None:
            item_index = self.item_select_index
        item_offset_y = sum(map(lambda item: item.item_box_height, self.droplist_items)[0:item_index])
        item_rect = self.droplist_items[item_index].item_box.get_allocation()
        return (0, item_offset_y, item_rect.width, item_rect.height)
        
    def active_item(self, item_index=None):
        '''Select item.'''
        global droplist_active_item
        
        if item_index == None:
            item_index = self.item_select_index
            
        if droplist_active_item:
            droplist_active_item.item_box.set_state(gtk.STATE_NORMAL)
                
        item = self.droplist_items[item_index]
        item.item_box.set_state(gtk.STATE_PRELIGHT)
        droplist_active_item = item
        
    def select_first_item(self):
        '''Select first item.'''
        if len(self.droplist_items) > 0:
            first_index = self.get_first_index()
            if first_index != None:
                self.item_select_index = first_index
                self.active_item()
        
                # Scroll to top.
                vadjust = self.item_scrolled_window.get_vadjustment()
                vadjust.set_value(vadjust.get_lower())
                
    def select_last_item(self):
        '''Select last item.'''
        if len(self.droplist_items) > 0:
            last_index = self.get_last_index()
            if last_index != None:
                self.item_select_index = last_index
                self.active_item()
    
                # Scroll to bottom.
                vadjust = self.item_scrolled_window.get_vadjustment()
                vadjust.set_value(vadjust.get_upper() - vadjust.get_page_size())
                
    def select_prev_item(self):
        '''Select preview item.'''
        if len(self.droplist_items) > 0:
            prev_index = self.get_prev_index()
            if prev_index != None:
                global droplist_active_item
                
                if droplist_active_item:
                    if self.item_select_index > 0:
                        self.item_select_index = prev_index
                        self.active_item()
                        
                        # Make item in visible area.
                        (item_x, item_y, item_width, item_height) = self.get_select_item_rect()
                        vadjust = self.item_scrolled_window.get_vadjustment()
                        if item_y < vadjust.get_value():
                            vadjust.set_value(item_y)
                else:
                    self.select_first_item()
    
    def select_next_item(self):
        '''Select next item.'''
        if len(self.droplist_items) > 0:
            next_index = self.get_next_index()
            if next_index != None:
                global droplist_active_item
                
                if droplist_active_item:
                    if self.item_select_index < len(self.droplist_items) - 1:
                        self.item_select_index = next_index
                        self.active_item()
                        
                        # Make item in visible area.
                        (item_x, item_y, item_width, item_height) = self.get_select_item_rect()
                        vadjust = self.item_scrolled_window.get_vadjustment()
                        if self.padding_y + item_y + item_height > vadjust.get_value() + vadjust.get_page_size():
                            vadjust.set_value(self.padding_y * 2 + item_y + item_height - vadjust.get_page_size())
                else:
                    self.select_first_item()
    
    def scroll_page_to_select_item(self):
        '''Scroll page to select item.'''
        (item_x, item_y, item_width, item_height) = self.get_select_item_rect()
        vadjust = self.item_scrolled_window.get_vadjustment()
        vadjust.set_value(min(max(vadjust.get_lower(), item_y - self.padding_y * 2), 
                              vadjust.get_upper() - vadjust.get_page_size()))
                    
    def scroll_page_up(self):
        '''Scroll page up.'''
        if len(self.droplist_items) > 0:
            # Scroll page up.
            vadjust = self.item_scrolled_window.get_vadjustment()
            vadjust.set_value(max(vadjust.get_lower(), vadjust.get_value() - vadjust.get_page_size()))
            
            # Select nearest item.
            item_infos = map(lambda (index, item): (index, self.get_select_item_rect(index)), enumerate(self.droplist_items))
            for (index, (item_x, item_y, item_width, item_height)) in item_infos:
                if item_y + self.padding_y > vadjust.get_value():
                    self.item_select_index = index
                    self.active_item()
                    break
    
    def scroll_page_down(self):
        '''Scroll page down.'''
        if len(self.droplist_items) > 0:
            # Scroll page up.
            vadjust = self.item_scrolled_window.get_vadjustment()
            vadjust.set_value(min(vadjust.get_upper() - vadjust.get_page_size(),
                                  vadjust.get_value() + vadjust.get_page_size()))
            
            # Select nearest item.
            item_infos = map(lambda (index, item): (index, self.get_select_item_rect(index)), enumerate(self.droplist_items))
            item_infos.reverse()
            for (index, (item_x, item_y, item_width, item_height)) in item_infos:
                if item_y + item_height + self.padding_y < vadjust.get_value() + vadjust.get_page_size():
                    self.item_select_index = index
                    self.active_item()
                    break
    
    def press_select_item(self):
        '''Press select item.'''
        if len(self.droplist_items) > 0:
            if 0 <= self.item_select_index < len(self.droplist_items):
                self.droplist_items[self.item_select_index].wrap_droplist_clicked_action()
    
    def droplist_key_press(self, widget, event):
        '''Key press event.'''
        key_name = get_keyevent_name(event)
        if self.keymap.has_key(key_name):
            self.keymap[key_name]()

        return True     
    
    def droplist_key_release(self, widget, event):
        '''Key press event.'''
        self.emit("key-release", 
                  self.items[self.item_select_index][0],
                  self.items[self.item_select_index][1],
                  self.item_select_index)    
        
    def expose_droplist_frame(self, widget, event):
        '''Expose droplist frame.'''
        cr = widget.window.cairo_create()        
        rect = widget.allocation

        with cairo_disable_antialias(cr):
            cr.set_line_width(1)
            cr.set_source_rgb(*color_hex_to_cairo(ui_theme.get_color("droplist_frame").get_color()))
            cr.rectangle(rect.x, rect.y, rect.width, rect.height)
            cr.fill()
        
    def get_droplist_item_at_coordinate(self, (x, y)):
        '''Get droplist item at coordinate, return None if haven't any droplist item at given coordinate.'''
        match_droplist_item = None
        
        item_heights = map(lambda item: item.item_box_height, self.droplist_items)
        item_offsets = map(lambda (index, height): sum(item_heights[0:index]), enumerate(item_heights))
        
        vadjust = self.item_scrolled_window.get_vadjustment()
        (scrolled_window_x, scrolled_window_y) = get_widget_root_coordinate(self.item_scrolled_window, WIDGET_POS_TOP_LEFT)
        for (index, droplist_item) in enumerate(self.droplist_items):
            item_rect = droplist_item.item_box.get_allocation()
            if is_in_rect((x, y), (scrolled_window_x, 
                                   scrolled_window_y + item_offsets[index] - (vadjust.get_value() - vadjust.get_lower()),
                                   item_rect.width, 
                                   item_rect.height)):
                match_droplist_item = droplist_item
                break
            
        return match_droplist_item
    
    def init_droplist(self, widget):
        '''Realize droplist.'''
        global root_droplists
        droplist_grab_window_focus_out()
        
        if not gtk.gdk.pointer_is_grabbed():
            droplist_grab_window_focus_in()
        
        if not self in root_droplists:
            root_droplists.append(self)
                            
    def get_subdroplists(self):
        '''Get subdroplists.'''
        if self.subdroplist:
            return [self.subdroplist] + self.subdroplist.get_subdroplists()
        else:
            return []
                
    def show(self, (x, y), (offset_x, offset_y)=(0, 0)):
        '''Show droplist.'''
        # Init offset.
        self.expect_x = x
        self.expect_y = y
        self.offset_x = offset_x
        self.offset_y = offset_y
        
        # Show.
        self.show_all()
        
    def adjust_droplist_position(self, widget):
        '''Realize droplist.'''
        # Adjust coordinate.
        (screen_width, screen_height) = get_screen_size(self)
        
        droplist_width = 0
        for droplist_item in self.droplist_items:
            if droplist_width == 0 and isinstance(droplist_item.item_box, gtk.Button):
                droplist_width = droplist_item.item_box_width
        droplist_width += self.padding_x * 2    
        droplist_height = self.allocation.height
        
        if self.x_align == ALIGN_START:
            dx = self.expect_x
        elif self.x_align == ALIGN_MIDDLE:
            dx = self.expect_x - droplist_width / 2
        else:
            dx = self.expect_x - droplist_width
            
        if self.y_align == ALIGN_START:
            dy = self.expect_y
        elif self.y_align == ALIGN_MIDDLE:
            dy = self.expect_y - droplist_height / 2
        else:
            dy = self.expect_y - droplist_height

        if self.expect_x + droplist_width > screen_width:
            dx = self.expect_x - droplist_width + self.offset_x
        if self.expect_y + droplist_height > screen_height:
            dy = self.expect_y - droplist_height + self.offset_y
            
        self.move(dx, dy)
            
    def hide(self):
        '''Hide droplist.'''
        # Hide current droplist window.
        self.hide_all()
        
        # Reset.
        self.subdroplist = None
        self.root_droplist = None
        
gobject.type_register(Droplist)

class DroplistItem(object):
    '''Droplist item.'''
    
    def __init__(self, droplist, index, item, font_size, 
                 droplist_padding_x, droplist_padding_y,
                 item_padding_left, item_padding_right, item_padding_y, max_width):
        '''Init droplist item.'''
        # Init.
        self.droplist = droplist
        self.index = index
        self.item = item
        self.font_size = font_size
        self.droplist_padding_x = droplist_padding_x
        self.droplist_padding_y = droplist_padding_y
        self.item_padding_left = item_padding_left
        self.item_padding_right = item_padding_right
        self.item_padding_y = item_padding_y
        self.subdroplist_active = False
        self.max_width = max_width
        self.arrow_padding_x = 5

        # Create.
        if self.item:
            self.create_droplist_item()
        else:
            self.create_separator_item()
        
    def create_separator_item(self):
        '''Create separator item.'''
        self.item_box = HSeparator(
            ui_theme.get_shadow_color("h_separator").get_color_info(),
            self.item_padding_left, 
            self.item_padding_y)
        self.item_box_height = self.item_padding_y * 2 + 1
        
    def create_droplist_item(self):
        '''Create droplist item.'''
        # Get item information.
        (item_content, item_value) = self.item[0:2]
        
        # Create button.
        self.item_box = gtk.Button()
        
        # Expose button.
        self.item_box.connect(
            "expose-event", 
            lambda w, e: self.expose_droplist_item(
                w, e, item_content))
        
        # Wrap droplist aciton.
        self.item_box.connect("button-press-event", lambda w, e: self.wrap_droplist_clicked_action())        
        
        self.item_box.connect("realize", lambda w: self.realize_item_box(w, item_content))
        
    def realize_item_box(self, widget, item_content):
        '''Realize item box.'''
        # Set button size.
        (width, height) = get_content_size(item_content, self.font_size)
        self.item_box_height = self.item_padding_y * 2 + int(height)
        self.item_box_width = self.item_padding_left + self.item_padding_right + int(width)

        if self.max_width != None:
            self.item_box_width = min(self.item_box_width, self.max_width)        
        else:
            self.item_box_width = self.item_box_width        
            
        self.item_box.set_size_request(self.item_box_width, self.item_box_height)        
        
    def wrap_droplist_clicked_action(self):
        '''Wrap droplist action.'''
        # Emit item-selected signal.
        self.droplist.emit("item-selected", self.item[0], self.item[1], self.index)
            
        # Hide droplist.
        droplist_grab_window_focus_out()
            
    def expose_droplist_item(self, widget, event, item_content):
        '''Expose droplist item.'''
        # Init.
        cr = widget.window.cairo_create()
        rect = widget.allocation
        font_color = ui_theme.get_color("menu_font").get_color()
        
        # Draw select effect.
        if self.subdroplist_active or widget.state in [gtk.STATE_PRELIGHT, gtk.STATE_ACTIVE]:
            # Draw background.
            draw_vlinear(cr, rect.x, rect.y, rect.width, rect.height, 
                         ui_theme.get_shadow_color("menu_item_select").get_color_info())
            
            # Set font color.
            font_color = ui_theme.get_color("menu_select_font").get_color()
            
        # Draw item content.
        draw_text(cr, item_content, 
                    rect.x + self.item_padding_left,
                    rect.y,
                    rect.width,
                    rect.height,
                    self.font_size, font_color,
                    )
        
        # Propagate expose to children.
        propagate_expose(widget, event)
    
        return True

