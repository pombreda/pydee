#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#    Copyright © 2009 Pierre Raybaut
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#    
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#    
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""
userconfig
==========

Module handling configuration files based on ConfigParser

Copyright © 2009 Pierre Raybaut
This software is licensed under the terms of the GNU General Public
License version 3 as published by the Free Software Foundation.
"""

import os
import os.path as osp
from ConfigParser import ConfigParser, MissingSectionHeaderError

__version__ = '1.0.0'

class NoDefault:
    pass

class UserConfig(ConfigParser):
    """
    UserConfig class, based on ConfigParser
    name: name of the config
    options: dictionnary containing options
             *or* list of tuples (section_name, options)
    
    Note that 'get' and 'set' arguments number and type
    differ from the overriden methods
    """
    
    default_section_name = 'Default'
    
    def __init__(self, name, defaults = None, load = True):
        ConfigParser.__init__(self)
        self.name = name
        if not isinstance(defaults, list):
            defaults = [ (self.default_section_name, defaults) ]
        self.defaults = defaults
        self.reset_to_defaults(save=False)
        # If config file already exists, it overrides Default options:
        if load:
            self.__load()
        # In any case, the resulting config is saved in config file:
        self.__save()

    def __load(self):
        """
        Load config from the associated .ini file
        """
        try:
            self.read(self.filename())
        except MissingSectionHeaderError:
            print "Warning: File contains no section headers."
        
    def __save(self):
        """
        Save config into the associated .ini file
        """
        conf_file = file(self.filename(),'w')
        self.write(conf_file)
        conf_file.close()
                
    def filename(self):
        """
        Create a .ini filename located in user home directory
        """
        return osp.join(osp.expanduser('~'), '.%s.ini' % self.name)
        
    def cleanup(self):
        """
        Remove .ini file associated to config
        """
        os.remove(self.filename())

    def reset_to_defaults(self, save=True):
        """
        Reset config to Default values
        """
        for section, options in self.defaults:
            self.add_section( section )
            for option in options:
                value = options[ option ]
                if not isinstance(value, (str, unicode)):
                    value = repr( value )
                ConfigParser.set(self, section, option, value)
        if save:
            self.__save()
        
    def __get_default(self, section, option):
        """
        Get Default value for a given (option, section)
        -> useful for type checking in 'get' method
        """
        for sec, options in self.defaults:
            if sec == section:
                return options[ option ]
                
    def get(self, section, option, default=NoDefault):
        """
        Get an option
        section=None: attribute a default section name
        default: default value (if not specified, an exception
        will be raised if option doesn't exist)
        """
        if section is None:
            section = self.default_section_name

        if not self.has_section(section):
            raise RuntimeError, "Unknown section"
        
        if not self.has_option(section, option):
            if default is NoDefault:
                raise RuntimeError, "Unknown option"
            else:
                return default
            
        value = ConfigParser.get(self, section, option)
        default_value = self.__get_default(section, option)
        if isinstance(default_value, bool):
            value = bool(value)
        elif isinstance(default_value, float):
            value = float(value)
        elif isinstance(default_value, int):
            value = int(value)
        elif not isinstance(default_value, (str, unicode)):
            try:
                # lists, tuples, ...
                value = eval(value)
            except:
                pass
        return value

    def set(self, section, option, value):
        """
        Set an option
        section=None: attribute a default section name
        """
        if section is None:
            section = self.default_section_name
        if not isinstance(section, (str, unicode)) \
           or not isinstance(option, (str, unicode)):
            raise RuntimeError, "'section' and 'option' must be strings"
        if section is None:
            section = self.default_section_name
        ConfigParser.set(self, section, option, value)
        self.__save()
