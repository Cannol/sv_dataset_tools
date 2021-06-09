from bases.sv_dataset import DatasetBase

dd = DatasetBase.D

for d in dd:
    attr_file = dd[d]['attr']
    with open(attr_file) as f:
        line = f.readlines()[0].strip()
    attrs = line.split(',')
    if len(attrs) == 9:
        line += ',0'
        with open(attr_file, 'w') as f:
            f.write(line)
        print('Fixed %s, which has %d attrs' % (attr_file, len(attrs)))
    elif len(attrs) < 9 or len(attrs) > 10:
        print('Error sequence attrs detected (len==%d): %s' % (len(attrs), attr_file))
print('--- Finished! ---')