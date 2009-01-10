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

__version__ = '1.0.2'

import os
import os.path as osp
from ConfigParser import ConfigParser, MissingSectionHeaderError

        
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

    def reset_to_defaults(self, save=True, verbose=False):
        """
        Reset config to Default values
        """
        for section, options in self.defaults:
            for option in options:
                value = options[ option ]
                self.__set(section, option, value, verbose)
        if save:
            self.__save()
        
    def __check_section_option(self, section, option):
        """
        Private method to check section and option types
        """
        if section is None:
            section = self.default_section_name
        elif not isinstance(section, (str, unicode)):
            raise RuntimeError, "Argument 'section' must be a string"
        if not isinstance(option, (str, unicode)):
            raise RuntimeError, "Argument 'option' must be a string"
        return section

    def get_default(self, section, option):
        """
        Get Default value for a given (option, section)
        -> useful for type checking in 'get' method
        """
        section = self.__check_section_option(section, option)
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
        section = self.__check_section_option(section, option)

        if not self.has_section(section):
            raise RuntimeError, "Unknown section"
        
        if not self.has_option(section, option):
            if default is NoDefault:
                raise RuntimeError, "Unknown option"
            else:
                return default
            
        value = ConfigParser.get(self, section, option)
        default_value = self.get_default(section, option)
        if isinstance(default_value, bool):
            value = eval(value)
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

    def __set(self, section, option, value, verbose):
        """
        Private set method
        """
        if not self.has_section(section):
            self.add_section( section )
        if not isinstance(value, (str, unicode)):
            value = repr( value )
        if verbose:
            print '%s[ %s ] = %s' % (section, option, value)
        ConfigParser.set(self, section, option, value)

    def set(self, section, option, value, verbose=False):
        """
        Set an option
        section=None: attribute a default section name
        """
        section = self.__check_section_option(section, option)
        default_value = self.get_default(section, option)
        if isinstance(default_value, bool):
            value = bool(value)
        elif isinstance(default_value, float):
            value = float(value)
        elif isinstance(default_value, int):
            value = int(value)
        elif not isinstance(default_value, (str, unicode)):
            value = repr(value)
        self.__set(section, option, value, verbose)
        self.__save()
