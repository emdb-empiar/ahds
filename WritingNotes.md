Notes about enabling Writing
============================

Fileformat(s) to write
----------------------
 * AmiraMesh 
 * HyperSurface (really necessary in first step)



Design
--------
 * Two stage:
   Split in two stages to simplify problem
   - First stage modifying Object structure by add and remove or methods which get
     passed python object and data array it should be represented by in file
   - second stage writing header content to file by using `__format__` special method
     for formatting outputs and `header.write` method receiving
     filename and replace Flag to force replacing exisitng file on disk
     or throw FileExists exception if not set or false.

 * First stage 
   - lowlevel interface:
     * Functions: `Block.add_attr`, `Block.rename_attr`, `Block.remove_attr`
     * Attributes: `Header._data_streams_block_list`
   - hilevel interface:
     * add_array
       code already implicitly present in `ahds.AmiraHeader._load_delartions` needs to be
       made explicit through refactor of `ahds.AmiraHeader._load_declarations`
     * add_stream/define element
       code already implict present in `ahds.AmiraHeader._load_definitions` needs to be 
       made explicit through refactor of `ahds.AmiraHeader._load_definitions`
     * add_parameter (+)
     * add_material (+)
     * remove_stream/remove_element
       the opposit to add_strean/add_element removes the element and thus the corresponding
       data stream again from the list of data_streams. (needs to be implemented)
     * remove_array
       implicitly calls remove_stream/remove_element for all elements still defined on array
       and removes array declaration/definition from `ahds.AmiraHeader`. (needs to be implemented)
     * remove_parameter (+)
     * remove_material (+)

  (+) just for convenience to ensure parameter structure is properly adjusted
      but in general it should be safe to call add_attr on any block within 
      parameters structure directly.

 * Second stage functions
   - all blocks implement `__format__` special method 
        + if not called with `">{level}"` format string assume level 0
     + loop through all items stored in attrs
     + for all non Block type items append row of
       `"{:>{indent}}{name:} {value:}\n".format('',indent=4*level,name='<name>',value=<item>)`
     + for all Block type items append
       `"{:>{indent}}{block.name:} {{\n{block:>{level}}\n}}".format('',indent=4*level,level=level+1,block<Block>)`
     + join list of strings on return by '\n'
     + use/abuse `>{indent}` and `>{level}` fromat codes to define much ascii texts
       representing block shall be indentented.
   - Header block has write method which
     + opens binary output stream for file name if not already open binary file/file like/stream object
     + outputs signature including endianess string and dimension if known
     + loops through `<Header>._data_streams_block_list` outputting for parent of each datastram
       `"{block.name} {block.dimension}\n".format(block=<block>).endcode('ascii')`
     + outputs `"{header.Parameters:>0}\n".format(header=self).encode('ascii')`
     + loops through `_data_streams_block_list` outputputting for all datastreams either
       `"{<block>.parent.name} {{ {block.type} {block.name} } @{index:d}".format(block=<block>,index=index).encode('ascii')` or
       `"{<block>.parent.name} {{ {block.type}[{block.dimension}] {block.name} } @{index:d}".format(block=<block>,index=index).encode('ascii')`
       dependent whether dimension is > 1 or not
       o if is field in addition outputs either
         `"Field {{ {block.type} {block.field_name} }} {block.interpolation_method}(@{index:})".format(block=<block>,index=index)` or
         `"Field {{ {block.type}[{block.dimension}] {block.field_name} }} {block.interpolation_method}(@{index:})".format(block=<block>,index=index)`
         dependent whether dimension is > 1 or not
     + loops through `_data_streams_block_list` calling for all datastreams 
       writes `\nb'@{}\n'.format(index).encode('ascii')` to output stream
       writes output of `<block>.encode()` method to output stream
     + closes output stream if opened by write
     + in case python or numy standard formatting differs from AmiraMesh requirements
       modify above format strings to directly format attribute instead of indirectly
       access through block parameter. Use Helperclassess to provide formatting
       `
       class DimensionFormatter():
            def __init__(self,dimension):
                self.dimension = dimension
            def __format__(self,formatspec):
                if np.isscalar(self.dimension):
                    return "{:{spec}}".format(self.dimension,spec=formatspec)
                if len(dimension) < 2:
                    return "{:{spec}}".format(self.dimension[0],spec=formatspec)
                return " ".join(
                    "{:{spec}}".format(item) for item in self.dimension
                )
       `
       Advantage any dimeension attribute needs just to be wrapped by DimensionFormatter
       to get appropriate formatting of array and type dimensions for example 
       `"{:d}".format(DimensionFormatter(header._data_streams_block_list[0].parent.dimension))`

   - Differences of `<Block>.__format__` compared to `<Block>.__str__`
     + only formats content of  `<Block>._attrs` and ingores any other
       attribute and property of `<Block>` stored in `__dict__` or defined
       on `__slots__`
     + outputs formatted header string represented by `<Block>` not tree
       view of object structure rooted at `<Block>`
     + indenting by fixed number based upon level number following right
       align symbol in format specification instead of indent string
     

TODO
----
  * Decide whether writing should be supported on Python 2.7 at all
    + not supporting writing on python 2.7 would allow to pick a simplier
      solution for the below issues
    + some solutions only reauire to exclude Python 2.7 support on windows
      which is anyway not supported at all
  * Check how Lists of numbers have to be output
  * Check how list of non block items are represented in memory
  * Check if format of lists can be altered directly or if a helper class for
    formatting lists in Amira Header style can handled by above approach
  * discuss if outputting comments should be supported and how
  * How to handle Structures which require meta arrays like HxSpreadSheet or HxSurface patches.
  * define which protective measures (overwriting files) are responasbilitiy of user, which
    would by nice when provided by and which a must be provided by ahds.
    + cleanest approache would be to maintain for each file a list of weak references 
      to all AmiraHeader/Amirafile objects which access it in in ONDEMMAND mode. Use the 
      (stat_result(<truefile>).st_dev,stat_result(<truefile>.st_ino) value pair to uniquely
      identfy each file.
    + use temporary hardlink to file opened in load on demmand mode and create a new file
      when writing the file instead of actually overwriting
      - for example write to a `*.am.part` file and hard link to final filename when done with
        writing, replacing the previous version.
      - Pro:
        o beyond a simple check if file is to be overwritten no further measures are necessary
        o is safe across different python processes and systems sharing same filesystem
        o least efforts to implement best maintainability
      - Con:
        o none yet
  * define if files/streams which are not seekable and can not be read multiple times should
    be handled directly by ahds at all (1)
    + should a future extension map ONDEMMAND mode on these files to IMMEDIATE mode as
      for HxSurface files
    + should a future extension should warp corresponding file objects in a `os.BufferedIO`
      object which on reading copies the content to temporary file and reads the next time
      opened from this file.
  * define if non seekable/rereadable files/streams should be directly written by ahds (1)
    + same considerations upon future extentions as for the previous point apply

(1) Pythons file/file-like io design allows to support these files by wrapping file handle
    within buffered-file object which even may be provided by caller -> support of any 
    thinkable stream possible using this approach including reading directly from and
    storing to archive files (tar,zip, etc.)

