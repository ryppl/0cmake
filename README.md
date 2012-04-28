0cmake
======

0compile utility for CMake-based Ryppl projects

Howto
-----

0cmake can be used in a Ryppl project's 0install feed to build and
install the feed from source.  For example:

```xml
    <command name='compile'>
     <runner interface='http://ryppl.github.com/feeds/ryppl/0cmake.xml'/>
       <arg>--component=bin</arg>
     </runner>
    </command>
```
