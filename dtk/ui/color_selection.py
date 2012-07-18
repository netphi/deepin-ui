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

from button import Button
from dialog import DialogBox, DIALOG_MASK_SINGLE_PAGE
from draw import draw_vlinear, draw_line, draw_pixbuf
from entry import TextEntry
from iconview import IconView
from label import Label
from locales import _
from scrolled_window import ScrolledWindow
from spin import SpinBox
from theme import ui_theme
import gobject
import gtk
from utils import (gdkcolor_to_string, color_hex_to_cairo, 
                   propagate_expose, alpha_color_hex_to_cairo,
                   color_hex_to_rgb, color_rgb_to_hex, cairo_disable_antialias,
                   is_hex_color, place_center)

class HSV(gtk.ColorSelection):
    '''HSV.'''
	
    def __init__(self):
        '''Init color selection.'''
        gtk.ColorSelection.__init__(self)
        
        # Remove right buttons.
        self.get_children()[0].remove(self.get_children()[0].get_children()[1])
        
        # Remove bottom color pick button.
        self.get_children()[0].get_children()[0].remove(self.get_children()[0].get_children()[0].get_children()[1])
        
    def get_hsv_widget(self):
        '''Get HSV widget.'''
        return self.get_children()[0].get_children()[0].get_children()[0]
    
    def get_color_string(self):
        '''Get color string.'''
        return gdkcolor_to_string(self.get_current_color())
    
    def get_rgb_color(self):
        '''Get rgb color.'''
        gdk_color = self.get_current_color()
        return (gdk_color.red / 256, gdk_color.green / 256, gdk_color.blue / 256)
    
gobject.type_register(HSV)

class ColorSelectDialog(DialogBox):
    '''Color select dialog.'''
    
    DEFAULT_COLOR_LIST = ["#000000", "#808080", "#E20417", "#F29300", "#FFEC00", "#95BE0D", "#008F35", "#00968F", "#FFFFFF", "#C0C0C0", "#E2004E", "#E2007A", "#920A7E", "#162883", "#0069B2", "#009DE0"]
	
    def __init__(self, confirm_callback=None, cancel_callback=None):
        '''Init color select dialog.'''
        DialogBox.__init__(self, _("Select color"), mask_type=DIALOG_MASK_SINGLE_PAGE)
        self.confirm_callback = confirm_callback
        self.cancel_callback = cancel_callback
        
        self.color_box = gtk.HBox()
        self.color_align = gtk.Alignment()
        self.color_align.set(0.5, 0.5, 0.0, 0.0)
        self.color_align.set_padding(10, 0, 8, 8)
        self.color_align.add(self.color_box)
        self.color_hsv = HSV()
        self.color_string = self.color_hsv.get_color_string()
        (self.color_r, self.color_g, self.color_b) = self.color_hsv.get_rgb_color()
        self.color_hsv.get_hsv_widget().connect(
            "button-release-event", 
            lambda w, e: self.update_color_info(self.color_hsv.get_color_string()))
        self.color_box.pack_start(self.color_hsv, False, False)
        
        self.color_right_box = gtk.VBox()
        self.color_right_align = gtk.Alignment()
        self.color_right_align.set(0.5, 0.5, 0.0, 0.0)
        self.color_right_align.set_padding(8, 0, 0, 0)
        self.color_right_align.add(self.color_right_box)
        self.color_box.pack_start(self.color_right_align)
        
        self.color_info_box = gtk.HBox()
        self.color_right_box.pack_start(self.color_info_box, False, False)
        
        self.color_display_box = gtk.VBox()
        self.color_display_button = gtk.Button()
        self.color_display_button.connect("expose-event", self.expose_display_button)
        self.color_display_button.set_size_request(70, 49)
        self.color_display_align = gtk.Alignment()
        self.color_display_align.set(0.5, 0.5, 1.0, 1.0)
        self.color_display_align.set_padding(5, 5, 5, 5)
        self.color_display_align.add(self.color_display_button)
        self.color_display_box.pack_start(self.color_display_align, False, False, 5)
        
        self.color_hex_box = gtk.HBox()
        self.color_hex_label = Label(_("Color value"))
        self.color_hex_box.pack_start(self.color_hex_label, False, False, 5)
        self.color_hex_entry = TextEntry(self.color_string)
        self.color_hex_entry.entry.check_text = is_hex_color
        self.color_hex_entry.entry.connect("press-return", self.press_return_color_entry)
        self.color_hex_entry.set_size(70, 24)
        self.color_hex_box.pack_start(self.color_hex_entry, False, False, 5)
        self.color_display_box.pack_start(self.color_hex_box, False, False, 5)
        
        self.color_info_box.pack_start(self.color_display_box, False, False, 5)
        
        self.color_rgb_box = gtk.VBox()
        self.color_r_box = gtk.HBox()
        self.color_r_label = Label(_("Red: "))
        self.color_r_spin = SpinBox(self.color_r, 0, 255, 1)
        self.color_r_spin.connect("value-changed", lambda s, v: self.click_rgb_spin())
        self.color_r_box.pack_start(self.color_r_label, False, False)
        self.color_r_box.pack_start(self.color_r_spin, False, False)
        self.color_g_box = gtk.HBox()
        self.color_g_label = Label(_("Green: "))
        self.color_g_spin = SpinBox(self.color_g, 0, 255, 1)
        self.color_g_spin.connect("value-changed", lambda s, v: self.click_rgb_spin())
        self.color_g_box.pack_start(self.color_g_label, False, False)
        self.color_g_box.pack_start(self.color_g_spin, False, False)
        self.color_b_box = gtk.HBox()
        self.color_b_label = Label(_("Blue: "))
        self.color_b_spin = SpinBox(self.color_b, 0, 255, 1)
        self.color_b_spin.connect("value-changed", lambda s, v: self.click_rgb_spin())
        self.color_b_box.pack_start(self.color_b_label, False, False)
        self.color_b_box.pack_start(self.color_b_spin, False, False)
        
        self.color_rgb_box.pack_start(self.color_r_box, False, False, 8)
        self.color_rgb_box.pack_start(self.color_g_box, False, False, 8)
        self.color_rgb_box.pack_start(self.color_b_box, False, False, 8)
        self.color_info_box.pack_start(self.color_rgb_box, False, False, 5)
        
        self.color_select_view = IconView()
        self.color_select_view.set_size_request(250, 60)
        self.color_select_view.connect("button-press-item", lambda view, item, x, y: self.update_color_info(item.color, False))
        self.color_select_view.draw_mask = self.get_mask_func(self.color_select_view)
        self.color_select_scrolled_window = ScrolledWindow()
        for color in self.DEFAULT_COLOR_LIST:
            self.color_select_view.add_items([ColorItem(color)])
            
        self.color_select_align = gtk.Alignment()
        self.color_select_align.set(0.5, 0.5, 1.0, 1.0)
        self.color_select_align.set_padding(10, 5, 6, 5)
        
        self.color_select_scrolled_window.add_child(self.color_select_view)
        self.color_select_scrolled_window.set_size_request(-1, 60)
        self.color_select_align.add(self.color_select_scrolled_window)
        self.color_right_box.pack_start(self.color_select_align, True, True)    
        
        self.confirm_button = Button(_("OK"))
        self.cancel_button = Button(_("Cancel"))
        
        self.confirm_button.connect("clicked", lambda w: self.click_confirm_button())
        self.cancel_button.connect("clicked", lambda w: self.click_cancel_button())
        
        self.right_button_box.set_buttons([self.confirm_button, self.cancel_button])
        self.body_box.pack_start(self.color_align, True, True)
        
        self.update_color_info(self.color_string)
        
    def click_confirm_button(self):
        '''Click confirm button.'''
        if self.confirm_callback != None:
            self.confirm_callback(self.color_hex_entry.get_text())
        
        self.destroy()
        
    def click_cancel_button(self):
        '''Click cancel button.'''
        if self.cancel_callback != None:
            self.cancel_callback()
        
        self.destroy()
        
    def click_rgb_spin(self):
        '''Click rgb spin.'''
        self.update_color_info(color_rgb_to_hex((self.color_r_spin.get_value(),
                                                 self.color_g_spin.get_value(),
                                                 self.color_b_spin.get_value())))        
        
    def press_return_color_entry(self, entry):
        '''Press return on color entry.'''
        self.update_color_info(entry.get_text())
        entry.select_all()
        
    def expose_display_button(self, widget, event):
        '''Expose display button.'''
        # Init.
        cr = widget.window.cairo_create()
        rect = widget.allocation
        
        cr.set_source_rgb(*color_hex_to_cairo(self.color_string))
        cr.rectangle(rect.x, rect.y, rect.width, rect.height)
        cr.fill()

        # Propagate expose.
        propagate_expose(widget, event)
        
        return True
        
    def update_color_info(self, color_string, clear_highlight=True):
        '''Update color info.'''
        self.color_string = color_string
        (self.color_r, self.color_g, self.color_b) = color_hex_to_rgb(self.color_string)
        self.color_r_spin.update(self.color_r)
        self.color_g_spin.update(self.color_g)
        self.color_b_spin.update(self.color_b)
        self.color_hex_entry.set_text(self.color_string)
        if not color_string.startswith("#"):
            color_string = "#" + color_string
        self.color_hsv.set_current_color(gtk.gdk.color_parse(color_string))
        
        if clear_highlight:
            self.color_select_view.clear_highlight()
        
        self.color_display_button.queue_draw()
        
gobject.type_register(ColorSelectDialog)

class ColorItem(gobject.GObject):
    '''Icon item.'''
	
    __gsignals__ = {
        "redraw-request" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }
    
    def __init__(self, color):
        '''Init item icon.'''
        gobject.GObject.__init__(self)
        self.color = color
        self.width = 20
        self.height = 16
        self.padding_x = 4
        self.padding_y = 4
        self.hover_flag = False
        self.highlight_flag = False
        
    def emit_redraw_request(self):
        '''Emit redraw-request signal.'''
        self.emit("redraw-request")
        
    def get_width(self):
        '''Get width.'''
        return self.width + self.padding_x * 2
        
    def get_height(self):
        '''Get height.'''
        return self.height + self.padding_y * 2
    
    def render(self, cr, rect):
        '''Render item.'''
        # Init.
        draw_x = rect.x + self.padding_x
        draw_y = rect.y + self.padding_y
        
        # Draw color.
        cr.set_source_rgb(*color_hex_to_cairo(self.color))
        cr.rectangle(draw_x, draw_y, self.width, self.height)
        cr.fill()
        
        if self.hover_flag:
            cr.set_source_rgb(*color_hex_to_cairo(ui_theme.get_color("color_item_hover").get_color()))
            cr.rectangle(draw_x, draw_y, self.width, self.height)
            cr.stroke()
        elif self.highlight_flag:
            cr.set_source_rgb(*color_hex_to_cairo(ui_theme.get_color("color_item_highlight").get_color()))
            cr.rectangle(draw_x, draw_y, self.width, self.height)
            cr.stroke()

        # Draw frame.
        with cairo_disable_antialias(cr):    
            cr.set_line_width(1)
            cr.set_source_rgb(*color_hex_to_cairo(ui_theme.get_color("color_item_frame").get_color()))
            cr.rectangle(draw_x, draw_y, self.width, self.height)
            cr.stroke()
            
    def icon_item_motion_notify(self, x, y):
        '''Handle `motion-notify-event` signal.'''
        self.hover_flag = True
        
        self.emit_redraw_request()
        
    def icon_item_lost_focus(self):
        '''Lost focus.'''
        self.hover_flag = False
        
        self.emit_redraw_request()
        
    def icon_item_highlight(self):
        '''Highlight item.'''
        self.highlight_flag = True

        self.emit_redraw_request()
        
    def icon_item_normal(self):
        '''Set item with normal status.'''
        self.highlight_flag = False
        
        self.emit_redraw_request()
    
    def icon_item_button_press(self, x, y):
        '''Handle button-press event.'''
        pass
    
    def icon_item_button_release(self, x, y):
        '''Handle button-release event.'''
        pass
    
    def icon_item_single_click(self, x, y):
        '''Handle single click event.'''
        pass

    def icon_item_double_click(self, x, y):
        '''Handle double click event.'''
        pass
    
gobject.type_register(ColorItem)

class ColorButton(gtk.VBox):
    '''Button.'''
	
    __gsignals__ = {
        "color-select" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (str,)),
    }
    
    def __init__(self, color="#FF0000"):
        '''Init button.'''
        gtk.VBox.__init__(self)
        self.button = gtk.Button()
        self.color = color
        self.width = 69
        self.height = 22
        self.color_area_width = 39
        self.color_area_height = 14
        
        self.button.set_size_request(self.width, self.height)
        self.pack_start(self.button, False, False)
        
        self.button.connect("expose-event", self.expose_button)
        self.button.connect("button-press-event", self.popup_color_selection_dialog)
        
    def popup_color_selection_dialog(self, widget, event):
        '''Popup color selection dialog.'''
        dialog = ColorSelectDialog(self.select_color)
        dialog.show_all()
        place_center(self.get_toplevel(), dialog)
        
    def select_color(self, color):
        '''Select color.'''
        self.set_color(color)
        self.emit("color-select", color)
        
    def set_color(self, color):
        '''Set color.'''
        self.color = color
        
        self.queue_draw()
        
    def get_color(self):
        '''Get color.'''
        return self.color
        
    def expose_button(self, widget, event):
        '''Expose button.'''
        # Init.
        cr = widget.window.cairo_create()
        rect = widget.allocation
        x, y, w, h = rect.x, rect.y, rect.width, rect.height
        
        # Get color info.
        if widget.state == gtk.STATE_NORMAL:
            text_color = ui_theme.get_color("button_font").get_color()
            border_color = ui_theme.get_color("button_border_normal").get_color()
            background_color = ui_theme.get_shadow_color("button_background_normal").get_color_info()
        elif widget.state == gtk.STATE_PRELIGHT:
            text_color = ui_theme.get_color("button_font").get_color()
            border_color = ui_theme.get_color("button_border_prelight").get_color()
            background_color = ui_theme.get_shadow_color("button_background_prelight").get_color_info()
        elif widget.state == gtk.STATE_ACTIVE:
            text_color = ui_theme.get_color("button_font").get_color()
            border_color = ui_theme.get_color("button_border_active").get_color()
            background_color = ui_theme.get_shadow_color("button_background_active").get_color_info()
        elif widget.state == gtk.STATE_INSENSITIVE:
            text_color = ui_theme.get_color("disable_text").get_color()
            border_color = ui_theme.get_color("disable_frame").get_color()
            disable_background_color = ui_theme.get_color("disable_background").get_color()
            background_color = [(0, (disable_background_color, 1.0)),
                                (1, (disable_background_color, 1.0))]
            
        # Draw background.
        draw_vlinear(
            cr,
            x + 1, y + 1, w - 2, h - 2,
            background_color)
        
        # Draw border.
        cr.set_source_rgb(*color_hex_to_cairo(border_color))
        draw_line(cr, x + 2, y + 1, x + w - 2, y + 1) # top
        draw_line(cr, x + 2, y + h, x + w - 2, y + h) # bottom
        draw_line(cr, x + 1, y + 2, x + 1, y + h - 2) # left
        draw_line(cr, x + w, y + 2, x + w, y + h - 2) # right
        
        # Draw four point.
        if widget.state == gtk.STATE_INSENSITIVE:
            top_left_point = ui_theme.get_pixbuf("button/disable_corner.png").get_pixbuf()
        else:
            top_left_point = ui_theme.get_pixbuf("button/corner.png").get_pixbuf()
        top_right_point = top_left_point.rotate_simple(270)
        bottom_right_point = top_left_point.rotate_simple(180)
        bottom_left_point = top_left_point.rotate_simple(90)
        
        draw_pixbuf(cr, top_left_point, x, y)
        draw_pixbuf(cr, top_right_point, x + w - top_left_point.get_width(), y)
        draw_pixbuf(cr, bottom_left_point, x, y + h - top_left_point.get_height())
        draw_pixbuf(cr, bottom_right_point, x + w - top_left_point.get_width(), y + h - top_left_point.get_height())
        
        # Draw color frame.
        cr.set_source_rgb(*color_hex_to_cairo("#c0c0c0"))
        cr.rectangle(x + (w - self.color_area_width) / 2,
                     y + (h - self.color_area_height) / 2,
                     self.color_area_width,
                     self.color_area_height)
        cr.stroke()
        
        # Draw color.
        cr.set_source_rgb(*color_hex_to_cairo(self.color))
        cr.rectangle(x + (w - self.color_area_width) / 2,
                     y + (h - self.color_area_height) / 2,
                     self.color_area_width,
                     self.color_area_height)
        cr.fill()

        # Draw mask when widget is insensitive.
        if widget.state == gtk.STATE_INSENSITIVE:
            cr.set_source_rgba(*alpha_color_hex_to_cairo(ui_theme.get_alpha_color("color_button_disable_mask").get_color_info()))
            cr.rectangle(x + (w - self.color_area_width) / 2,
                         y + (h - self.color_area_height) / 2,
                         self.color_area_width,
                         self.color_area_height)
            cr.fill()
        
        return True
        
gobject.type_register(ColorButton)
