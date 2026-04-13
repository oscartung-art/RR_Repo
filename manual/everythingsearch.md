# everythingSearch Manual

# .metadata.efu

1. note that for some reason .metadata.efu cannot exists at the root of the share drive (i.e. not on g:/, but on g:/3D it's okay)
.metadata.efu are sidecar files used to describe property values for files/folders.

File Format
Lookup Behavior
Filename Rules
CSV Rules
Encoding
Property Value Syntax
Why efu?
Why .metadata.efu?
.metadata.efu in Everything



File Format

.metadata.efu files are CSV files.
The CSV header describes the property type for each column.
There must be a Filename column.

.metadata.efu example:
Code: Select all

Filename,Rating,Tags
"file.txt",75,"My Tags"
file.txt in the same location as this .metadata.efu will have a rating of 75 (4/5 stars)
file.txt in the same location as this .metadata.efu will have the tag: My Tags



Lookup Behavior

When retrieving property values, .metadata.efu files are checked starting from the location of the target file or folder and moving up the directory hierarchy toward the root.

Lookup stops once a non-NULL property value is found.

For example, the file 
C:\folder\subfolder\file.txt
 will check for properties in the following .metadata.efu files:
c:\folder\subfolder\.metadata.efu
c:\folder\.metadata.efu
c:\.metadata.efu




Filename Rules

Filenames on Windows are case insensitive.
Case sensitive on unix.



Filenames are relative to the .metadata.efu
/ or \ can be used as a path separator on Windows.
/ is the path separator on unix.
Relative filenames can not go up directories (no ..)



CSV Rules

In the case of duplicated columns, the last column is used.

In the case of duplicated items, the last item is used.



A CSV cell with no text is null.
Use "" for an empty value.
null values are treated as no value.

Use "" inside quotes to escape a literal double quote (")



Encoding

.metadata.efu files should be encoded with UTF-8.
A UTF-8 BOM is recommended, but not required.



Property Value Syntax

Date syntax is Windows FILETIME in decimal or ISO-8601.

Rating syntax is: 1 (1/5 star) to 99 (5/5 stars)

Length/Duration syntax is: A 100 nanosecond interval (Windows FILETIME) or [[[d:]hh:]mm:]ss[.SSSSSSS]

Multi-string syntax: A semicolon (;) delimited list of strings.
Use ; inside literal double quotes (") to escape a literal ;
Use "" inside double quotes to escape a literal double quote in CSV.

Common properties:
Width	Integer
Height	Integer
Bit Depth	Integer
Length	Length/Duration
Audio Sample Rate	Integer
Audio Channels	Integer
Audio Bits Per Sample	Integer
Audio Format	String
Title	String
Artist	String
Album	String
Year	Integer
Comment	String
Track	Integer
Genre	String
Frame Rate	Double
Video Format	String
Rating	Integer 1-99
Tags	Multi-String
CRC32	Hex-String
CRC64	Hex-String
MD5	Hex-String
SHA1	Hex-String
SHA256	Hex-String
SHA384	Hex-String
SHA512	Hex-String
Description	String
Version	String
Subject	String
Authors	Multi-String
Date Taken	Date
Software	String
Copyright	String



Why efu?
EFU/CSV is well defined and will not change.
EFU files can be opened in Everything.
Human readable/editable.

EFU File Lists



Why .metadata.efu?
Following other standards where files starting with . are usually hidden. (.htaccess .gitignore)
There's already .metadata on unix which is a binary file.



.metadata.efu in Everything

Everything 1.5 will support .metadata.efu sidecar files for most Everything properties and Property System properties.
This does not include the size, date modified, date created, date access, attributes and other indexed values (like name length).

Everything will lookup .metadata.efu files from your index.
Lookup is instant and free.



.metadata.efu files are cached.
Everything will not automatically update property values for files/folders if you modify the .metadata.efu externally.
Support for live updates might be added in a future version.

To refresh property values after modifying your .metadata.efu externally:
In Everything, press F5 to refresh properties.
To refresh indexed property values after modifying your .metadata.efu externally:
In Everything, Select your indexed property values.
press Ctrl + F5 to refresh indexed properties.


Everything gives priority to .metadata.efu properties.
If no property value is specified, Everything will continue checking the Windows Property System / built-in property handler for property values.

Property Gathering Priority



To disable .metadata.efu files:
In Everything 1.5, from the Tools menu, click Options.
Click the Advanced tab on the left.
To the right of Show settings containing, search for:
metadata
Select: metadata_efu
Set the value to: false
Click OK.
.metadata.efu files are enabled by default.



To only search the target file/folder location for a .metadata.efu file
In Everything 1.5, from the Tools menu, click Options.
Click the Advanced tab on the left.
To the right of Show settings containing, search for:
metadata
Select: metadata_efu_max_search_depth
Set the value to: 0
Click OK.
Use 255 to search all the way to the root.
Set to 0 to only search the same location as the target file/folder.
Set to 1 to only search the same location and parent folder as the target file/folder.
Everything will search all the way to the root by default.



To search for files with a defined .metadata.efu property value, include the following in your search:
is-metadata-efu-property:




To search for files with a defined .metadata.efu property value for a specific property, include the following in your search:
is-metadata-efu-property:<property-canonical-name>


where <property-canonical-name> is the specific property.

For example, to find files/folders with a tag from a .metadata.efu file, include the following in your search:
is-metadata-efu-property:tag

---

See the standalone reference: [Everything Search Reference](everythingsearch_reference.md)


