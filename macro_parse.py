def find_value(dictionary, target_column, target_value):
    for key, value in dictionary.items():
        if value[target_column] == target_value:
            return key
    return None


def update_mdt(instruction: str, mdt_index: int, mdt):
    mdt[mdt_index] = {
        'index': mdt_index,
        'instruction': instruction
    }
    mdt_index += 1
    return mdt_index


def update_ala_and_mnt(lineparts: str, ala: dict, ala_index: int, mdt_index: int, mnt: dict, mnt_index: int):
    if lineparts[0].find('&') > 0:
        mnt[mnt_index] = {
            'index': mnt_index,
            'name': lineparts[1],
            'mdt index': mdt_index,
        }
        mnt_index += 1
        ala[ala_index] = {
            'index': ala_index,
            'dummy argument': lineparts[0].replace(',', ''),
            'index marker': '#0',
        }
        ala_index += 1
        for i in range(1, len(lineparts)-1):
            ala[ala_index] = {
                'index': ala_index,
                'dummy argument': lineparts[i+1].replace(',', ''),
                'index marker': f'#{i}',
            }
            ala_index += 1
    else:
        mnt[mnt_index] = {
            'index': mnt_index,
            'name': lineparts[0],
            'mdt index': mdt_index,
        }
        mnt_index += 1
        for i in range(1, len(lineparts)):
            ala[ala_index] = {
                'index': ala_index,
                'dummy argument': lineparts[i].replace(',', ''),
                'index marker': f'#{i}',
            }
            ala_index += 1

    return ala_index, mnt_index


def expand_macro(start_mdt_index: int, macro_arguments: list, mnt: dict, mdt: dict, ala: dict):
    code = ''
    start_dummy_params = mdt[start_mdt_index]['instruction'].split(' ')[1:]
    for i in range(len(macro_arguments)):
        key = find_value(ala, 'dummy argument',
                         start_dummy_params[i].replace(',', ''))
        if key != None:
            ala[key]['actual argument'] = macro_arguments[i]
    start_mdt_index += 1
    while True:
        instruction = mdt[start_mdt_index]['instruction']
        parti = instruction.split(' ')
        for i in range(len(parti)):
            if '#' in parti[i]:
                j = parti[i].find('#')
                parti[i] = macro_arguments[int(parti[i][j+1])-1]
        if instruction == 'MACRO':
            start_mdt_index += 1
            inssub = mdt[start_mdt_index]['instruction']
            partsub = inssub.split(' ')
            for i in range(len(partsub)):
                if '#' in partsub[i]:
                    j = partsub[i].find('#')
                    partsub[i] = macro_arguments[int(partsub[i][j+1])-1]
            mdt_index = len(mdt) + 1
            mnt_index = len(mnt) + 1
            ala_index = len(ala) + 1
            ala_index, mnt_index = update_ala_and_mnt(
                partsub, ala, ala_index, mdt_index, mnt, mnt_index)
            mdt_index = update_mdt(" ".join(partsub), mdt_index, mdt)
            start_mdt_index += 1
            while inssub != 'MEND':
                inssub = mdt[start_mdt_index]['instruction']
                partsub = inssub.split(' ')
                for i in range(len(partsub)):
                    if '#' in partsub[i]:
                        j = partsub[i].find('#')
                        partsub[i] = macro_arguments[int(partsub[i][j+1])-1]
                for i in range(len(partsub)):
                    if partsub[i].find('&') >= 0:
                        arg = partsub[i]
                        index = next(
                            (item['index marker'] for item in ala.values() if item['dummy argument'] == arg), None)
                        if index:
                            partsub[i] = index

                mdt_index = update_mdt(" ".join(partsub), mdt_index, mdt)
                start_mdt_index += 1
            start_mdt_index -= 1
        else:
            if instruction == 'MEND':
                break
            code += " ".join(parti) + '\n'
        start_mdt_index += 1
    return code


def parse_assembly_code(file_path):
    with open(file_path, 'r') as file:
        code = file.readlines()

    mnt = {}
    mdt = {}
    ala = {}
    expanded_source_code = ""

    mnt_index = 1
    ala_index = 1
    mdt_index = 1
    macro_flag = 0
    prev = ''
    for line in code:
        line = line.strip()

        if line == '':
            continue

        if line == 'MACRO':
            macro_flag += 1
            if macro_flag == 1:
                prev = line
                continue

        if line == 'MEND':
            macro_flag -= 1
            prev = line
            mdt[mdt_index] = {
                'index': mdt_index,
                'instruction': line
            }
            mdt_index += 1
            continue

        if macro_flag > 0:
            line_parts = line.split(' ')

            if macro_flag == 1 and prev == 'MACRO':
                ala_index, mnt_index = update_ala_and_mnt(
                    line_parts, ala, ala_index, mdt_index, mnt, mnt_index)
            else:
                for i in range(len(line_parts)):
                    if line_parts[i].find('&') >= 0:
                        arg = line_parts[i]
                        index = next(
                            (item['index marker'] for item in ala.values() if item['dummy argument'] == arg), None)
                        if index:
                            line_parts[i] = index

            mdt_index = update_mdt(" ".join(line_parts), mdt_index, mdt)
        else:
            macro_match = next(
                (macro for macro in mnt.values() if macro['name'] in line), None)
            if macro_match:
                start_mdt_index = macro_match['mdt index']
                macro_arguments = line.replace(',', '').split(' ')[1:]
                expanded_source_code += expand_macro(start_mdt_index,
                                                     macro_arguments, mnt, mdt, ala)
            else:
                expanded_source_code += line + '\n'

        prev = line

    with open('expanded_source_code.txt', 'w') as expanded_file:
        expanded_file.write(expanded_source_code)
    return mnt, mdt, ala


def write_table_to_file(table, file_path):
    with open(file_path, 'w') as file:
        if len(table) > 0:
            column_widths = {key: len(key) for key in table[1].keys()}
            for row in table.values():
                for key, value in row.items():
                    column_widths[key] = max(
                        column_widths[key], len(str(value)))

            header = "\t".join(
                key.ljust(column_widths[key]) for key in table[1].keys())
            file.write(f"{header}\n")

            for row in table.values():
                values = "\t".join(str(row[key]).ljust(
                    column_widths[key]) for key in row.keys())
                file.write(f"{values}\n")


def main():
    file_path = 'question.txt'
    mnt, mdt, ala = parse_assembly_code(file_path)
    write_table_to_file(mnt, 'mnt_table.txt')
    print("MNT Table generated at: ./mnt_table.txt")
    write_table_to_file(mdt, 'mdt_table.txt')
    print("MDT Table generated at: ./mdt_table.txt")
    write_table_to_file(ala, 'ala_table.txt')
    print("ALA Table generated at: ./ala_table.txt")

    print("Expanded source code generated at: ./expanded_source_code.txt")


if __name__ == '__main__':
    main()
