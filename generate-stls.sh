#!/bin/bash
for file in ./parts/*.scad; do
    filePath="${file%.*}"
    inferredPath=$(echo "$filePath" | sed "s/.\/parts\///g")
    # For debugging
    # echo "$filePath -> $inferredPath"
    openscad "$filePath.scad" -o "./generated/$inferredPath.stl"
done
