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

from constant import BUTTON_NORMAL, BUTTON_PRESS, BUTTON_HOVER
from draw import draw_pixbuf
from utils import widget_fix_cycle_destroy_bug, propagate_expose
import gobject
import gtk

class ImageButtonGroup(gtk.HBox):
    
    def __init__(self, items, spacing=5):
        gtk.HBox.__init__(self)
        self.item_index = 0
        
        self.set_spacing(spacing)
        # Init item
        if items:
            for index, item in enumerate(items):
                image_button_item = ImageButtonItem(item, index, self.set_index, self.get_index)
                self.pack_start(image_button_item)
        self.show_all()        
        
    def set_index(self, index):    
        self.queue_draw()
        self.item_index = index
        
    def get_index(self):    
        return self.item_index
    
gobject.type_register(ImageButtonGroup)

class ToggleButtonGroup(gtk.HBox):
    
    def __init__(self, items, spacing=5):
        gtk.HBox.__init__(self)
        self.item_index = -1
        self.set_spacing(spacing)

        # Init item
        if items:
            for index, item in enumerate(items):
                toggle_button_item = ToggleButtonItem(item, index, self.set_index, self.get_index)
                self.pack_start(toggle_button_item)
                
        self.show_all()        
        
    def set_index(self, index):    
        self.queue_draw()
        self.item_index = index
        
    def get_index(self):    
        return self.item_index
    
    def is_active(self):
        return self.item_index != -1
    
gobject.type_register(ToggleButtonGroup)

class ImageButtonItem(gtk.Button):
    
    def __init__(self, item, index, set_index, get_index):
        gtk.Button.__init__(self)
        
        self.index = index
        self.set_index = set_index
        self.get_index = get_index
        
        (self.normal_dpixbuf, self.hover_dpixbuf, self.press_dpixbuf, self.clicked_callback) = item
        
        # Init item button.    
        pixbuf = self.normal_dpixbuf.get_pixbuf()
        self.set_size_request(pixbuf.get_width(), pixbuf.get_height())    
        widget_fix_cycle_destroy_bug(self)
        self.connect("expose-event", self.expose_button_item)
        self.connect("clicked", lambda w: self.wrap_button_item_clicked_action())
        
    def wrap_button_item_clicked_action(self):    
        if self.clicked_callback:
            self.clicked_callback()
        self.set_index(self.index)    
        
    def expose_button_item(self, widget, event):    
        
        # Init.
        cr = widget.window.cairo_create()
        rect = widget.allocation
        select_index = self.get_index()
        
        # Draw background
        if widget.state == gtk.STATE_NORMAL:
            if select_index == self.index:
                select_status = BUTTON_PRESS
            else:    
                select_status = BUTTON_NORMAL
                
        elif widget.state == gtk.STATE_PRELIGHT:        
            if select_index == self.index:
                select_status = BUTTON_PRESS
            else:    
                select_status = BUTTON_HOVER
                
        elif widget.state == gtk.STATE_ACTIVE:   
            select_status = BUTTON_PRESS
            
        if select_status == BUTTON_PRESS:    
            pixbuf = self.press_dpixbuf.get_pixbuf()
        elif select_status == BUTTON_NORMAL:    
            pixbuf = self.normal_dpixbuf.get_pixbuf()
        elif select_status == BUTTON_HOVER:    
            pixbuf = self.hover_dpixbuf.get_pixbuf()
            
        draw_pixbuf(cr, pixbuf, rect.x, rect.y)    
        propagate_expose(widget, event)
        return True
    
gobject.type_register(ImageButtonItem)    


class ToggleButtonItem(gtk.ToggleButton):
    
    def __init__(self, item, index, set_index, get_index):
        gtk.ToggleButton.__init__(self)
        
        self.index = index
        self.set_index = set_index
        self.get_index = get_index
        
        (self.inactive_dpixbuf, self.active_dpixbuf, 
         self.inactive_hover_dpixbuf, self.active_hover_dpixbuf, self.toggled_callback) = item
        
        pixbuf = self.inactive_dpixbuf.get_pixbuf()
        self.set_size_request(pixbuf.get_width(), pixbuf.get_height())
        widget_fix_cycle_destroy_bug(self)
        self.connect("expose-event", self.expose_toggle_button_item)
        self.connect("toggled", lambda w: self.wrap_toggle_button_clicked_action())
        self.connect("button-press-event", lambda w,e: self.set_index(self.index))
        
    def wrap_toggle_button_clicked_action(self):    
        if self.toggled_callback:
            self.toggled_callback()
        
    def expose_toggle_button_item(self, widget, event):    
        
        # Init.
        cr = widget.window.cairo_create()
        rect = widget.allocation
        select_index = self.get_index()
        
        if widget.state == gtk.STATE_NORMAL:
            if select_index == self.index:
                self.set_index(-1)
            pixbuf = self.inactive_dpixbuf.get_pixbuf()
        elif widget.state == gtk.STATE_PRELIGHT:        
            if not self.inactive_hover_dpixbuf and not self.active_hover_dpixbuf:
                if widget.get_active():
                    pixbuf = self.active_dpixbuf.get_pixbuf()
                else:    
                    pixbuf = self.inactive_dpixbuf.get_pixbuf()
            else:    
                if self.inactive_hover_dpixbuf and self.active_hover_dpixbuf:
                    if widget.get_active():
                        pixbuf = self.active_hover_dpixbuf.get_pixbuf()
                    else:    
                        pixbuf = self.inactive_hover_dpixbuf.get_pixbuf()
                elif self.inactive_hover_dpixbuf:        
                    pixbuf = self.inactive_hover_dpixbuf.get_pixbuf()
                elif self.active_hover_dpixbuf:    
                    pixbuf = self.active_hover_dpixbuf.get_pixbuf()
                
        elif widget.state == gtk.STATE_ACTIVE:        
            if select_index == self.index:
                pixbuf = self.active_dpixbuf.get_pixbuf()            
            else:    
                widget.set_active(False)                
                pixbuf = self.inactive_dpixbuf.get_pixbuf()                
                
        draw_pixbuf(cr, pixbuf, rect.x, rect.y)    
        propagate_expose(widget, event)
        return True
        
gobject.type_register(ToggleButtonItem)    
        
        
        
        
