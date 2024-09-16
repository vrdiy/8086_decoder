# Adds spacing between lines based on first word
def add_spacing(str : str) -> str:
    lines = str.splitlines()
    prev_word = lines[0].split(' ')[0]
    out = ''

    # Flag for if a consecutive grouping is currently formed
    is_consecutive_grouping = False

    for i in range(0,len(lines)):
        first_word = lines[i].split(' ')[0]

        # If a new first word is encountered...
        if first_word != prev_word:

            # and there was already a consecutive grouping
            if is_consecutive_grouping == True:

                # Break this grouping 
                prev_word = first_word
                is_consecutive_grouping = False
                out += '\n'

            # and there wasn't already a consecutive grouping
            # Check bounds before looking at next line
            elif i < len(lines)-1:

                # If the next word is the same as this new word, make a new grouping
                if lines[i+1].split(' ')[0] == first_word:
                    prev_word = first_word
                    out += '\n'

                # This code path is taken by non-consecutive groups
                # Doing nothing here allows non-consecutive groups to form
                else:
                    #out += ';----------\n'
                    pass

        # Else the lines are a consecutive group
        else:
            is_consecutive_grouping = True
        out += lines[i] + '\n'
    
    return out

