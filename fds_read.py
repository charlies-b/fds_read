import argparse
import re
"""
cmd line fds file reader
"""
class Model: # model 'data type'
    def __init__(self, CHID=None):
        self.CHID=CHID # &HEAD 
        self.SOOT_YIELD=None # &REAC
        self.CO_YIELD=None
        self.HEAT_OF_COMBUSTION=None
        self.RADIATIVE_FRACTION=None
        self.surfs=[] # &SURF
        self.vents=[] # &VENT
    
    def set_CHID(self, CHID):
        self.CHID=CHID

    def set_SOOT_YIELD(self, SOOT_YIELD):
        self.SOOT_YIELD=SOOT_YIELD
    
    def set_CO_YIELD(self, CO_YIELD):
        self.CO_YIELD=CO_YIELD

    def set_HEAT_OF_COMBUSTION(self, HEAT_OF_COMBUSTION):
        self.HEAT_OF_COMBUSTION=HEAT_OF_COMBUSTION

    def set_RADIATIVE_FRACTION(self, RADIATIVE_FRACTION):
            self.RADIATIVE_FRACTION=RADIATIVE_FRACTION

    def add_VENT(self, vent):
        self.vents.append(vent)

    def add_SURF(self, surf):
        self.surfs.append(surf)
    
    def calc_Peak_HRR(self, fire_area, HRRPUA):
        """
        Calculate FDS Peak HRR from fire_area
        """
        return HRRPUA*fire_area
    
    def calc_Alpha(self, peak_hrr, tau_q):
        """
        Calculate FDS Growth Rate Coefficient from Peak HRR
        """
        return peak_hrr/(tau_q)**2
    
    
    def calculate_BURNER(self, vent, surf):
        alpha_classifications = {'Slow':0.003, 'Medium':0.012, 'Fast':0.047, 'Ultra-fast':0.188} # kW/s^2
        peakHRR = self.calc_Peak_HRR(vent.calc_Area(), surf.HRRPUA)
        alpha = self.calc_Alpha(peakHRR,surf.TAU_Q )
        alpha_diff = {key : abs(alpha_classifications[key]-alpha) for key in alpha_classifications}
        alpha_class = min(alpha_diff, key=alpha_diff.get)
        return peakHRR, alpha, alpha_class
    
    def print_summary(self):
        """
        Print model summary
        """
        summary_string = \
            '\nMODEL:'\
            '\n  CHID: {0} \n' \
            '\nREAC PARAMETERS:' \
            '\n  SOOT_YIELD: {1} [kg/kg]' \
            '\n  CO_YIELD: {2} [kg/kg]' \
            '\n  HEAT_OF_COMBUSTION: {3:.2e} [kJ/kg]' \
            '\n  RADIATIVE_FRACTION: {4}'\
            .format(
                self.CHID,
                self.SOOT_YIELD,
                self.CO_YIELD,
                self.HEAT_OF_COMBUSTION,
                self.RADIATIVE_FRACTION
            )
        summary_string += \
            '\n' \
            '\nVENTS'
        for vent in self.vents:
            summary_string += '\n  ID: '+ vent.ID + ', SURF_ID:' + vent.SURF_ID
        for vent in self.vents:
            for surf in self.surfs:
                if vent.SURF_ID == surf.ID == 'BURNER': # ASSUME caluations are for 'BURNER'
                    peakHRR, alpha, alpha_class= self.calculate_BURNER(vent, surf)
                    summary_string += \
                    '\n' \
                    '\nCALCULATION, SURF_ID: BURNER'\
                         '\n  VENT: {0}'\
                        '\n  FIRE_AREA: {1} [m²]'\
                        '\n  HRRPUA: {2} [kW/m²]'\
                        '\n  TAU_Q: {3} [s] '\
                        '\n  PEAK_HRR: {4} [kW]'\
                        '\n  ALPHA: {5:.3f} [kW/s²]'\
                        '\n  ALPHA CLASSIFICATION: {6}'\
                        '\n' \
                        .format(
                            vent.ID,
                            vent.calc_Area(),
                            surf.HRRPUA,
                            surf.TAU_Q,
                            peakHRR,
                            alpha,
                            alpha_class
                        )
                 # could add logic for other VENT calculations with other SURF_ID
        print(summary_string)
        return summary_string       

class Vent: # vent 'data type' 
    def __init__(self, ID=None):
        self.ID=ID # &VENT
        self.SURF_ID=None 
        self.XB=None
        self.x1=None
        self.x2=None
        self.y1=None
        self.y2=None
        self.z1=None
        self.z2=None

    def set_ID(self, ID):
        self.ID=ID 

    def set_SURF_ID(self, SURF_ID):
        self.SURF_ID=SURF_ID
    
    def set_XB(self, XB):
        assert(len(XB)==6)
        self.XB=XB
        self.x1=XB[0]
        self.x2=XB[1]
        self.y1=XB[2]
        self.y2=XB[3]
        self.z1=XB[4]
        self.z2=XB[5]

    def calc_Area(self):
        return (self.x2-self.x1)*(self.y2-self.y1)

class Surf: # surf 'data type'
        def __init__(self, ID=None):

            self.HRRPUA=None # &SURF
            self.TAU_Q=None
       
        def set_ID(self, ID):
            self.ID=ID
       
        def set_HRRPUA(self, HRRPUA):
            self.HRRPUA=HRRPUA
    
        def set_TAU_Q(self, TAU_Q):
            self.TAU_Q=TAU_Q

def get_stringValue(value_string):
    """
    Gets a string value from a value as a string
    """
    return str(value_string.strip('\' /'))

def get_floatValue(value_string):

    """
    Gets a float value from a value as a string
    """
    return float(value_string.strip('\' /'))

def get_XB_Value(value_string):
    """
    Gets 1d array of floats from a sting of floats delimited by ,
    """
    return [get_floatValue(s) for s in value_string.split(',') ]

def parse_HEAD(block, model): # ASSUME HEAD attributes
    """
    sets HEAD atttibutes in model from HEAD block as string
    """
    assert(block[0:len('&HEAD')]) == '&HEAD' 
    params = block[len('&HEAD'):].split(',') # ASSUME comma-separted key=value pairs
    for param in params:
        param = param.strip(' /').split('=') # ['key', 'value']
        if param[0].strip()=='CHID': # key
            value = get_stringValue(param[1]) # expect string value
            model.set_CHID(value)

def parse_REAC(block, model): # ASSUME REAC attributes
    """
    sets REAC atttibutes in model from REAC block as string
    """
    assert(block[0:len('&REAC')]) == '&REAC' 
    params = block[len('&REAC'):].split(',') # ASSUME comma-separted key=value pairs

    for param in params:
        param = param.strip(' /').split('=')
        if param[0].strip()=='SOOT_YIELD':
            value = get_floatValue(param[1]) # expect float
            model.set_SOOT_YIELD(value)
        if param[0]=='CO_YIELD':
            value = get_floatValue(param[1]) # expect float
            model.set_CO_YIELD(value)
        if param[0]=='HEAT_OF_COMBUSTION':
            value = get_floatValue(param[1]) # expect float
            model.set_HEAT_OF_COMBUSTION(value)
        if param[0]=='RADIATIVE_FRACTION':
            value = get_floatValue(param[1]) # expect float
            model.set_RADIATIVE_FRACTION(value)

def parse_SURF(block, surf): # ASSUME SURF attributes
    """
    sets atttibutes in surf from SURF block as string
    """
    assert(block[0:len('&SURF')]) == '&SURF' 
    params = block[len('&SURF'):].split(',') # ASSUME comma-separted key=value pairs

    for param in params:
        param = param.strip(' /').split('=')
        if param[0]=='ID':
            value = get_stringValue(param[1]) # expect string value
            surf.set_ID(value)
        if param[0]=='HRRPUA':
            value = get_floatValue(param[1]) # expect float
            surf.set_HRRPUA(value)
        if param[0]=='TAU_Q':
            value = get_floatValue(param[1]) # expect float
            surf.set_TAU_Q(value)

def parse_VENT(block, vent): # ASSUME VENT attributes
    """
    Parse VENT block as string and set atttibutes in Vent object 
    """
    assert(block[0:len('&VENT')]) == '&VENT' 
    params = block[len('&VENT'):] # used regex – inconsistent deliminator; key=value, key=value,value,value 
    # ID regex
    param = re.search( # search for ID key value pair string in parameter string
        "[\s,]ID=\'[a-zA-Z\s]+\'" ,
        params).group()
    param = param.strip(' /,').split('=') # ['key','value']
    value = get_stringValue(param[1])
    vent.set_ID(value)

    # SURF_ID regex
    param = re.search( # search for SURF_ID key value pair string in parameter string
        "SURF_ID=\'[a-zA-Z\s]+\'" ,
        params).group()
    param = param.strip(' /,').split('=') # ['key','value']
    value = get_stringValue(param[1])
    vent.set_SURF_ID(value)

    # XB regex
    param = re.search( # search for SURF_ID key value pair string in parameter string
        "XB=[0-9\.,\s]+[\s|/|,]" ,
        params).group()
    param = param.strip(' /,').split('=') # ['key','value']
    value = get_XB_Value(param[1])
    vent.set_XB(value)

def read_fds(path):
    """
    Read FDS file return Model object
    """
    blocks = read_blocks(path)
    model = parse_blocks(blocks)
    return model

def read_blocks(path):
    """
    Read FDS file and return list of parameter blocks as strings
    """
    with open(path) as f: # read file as list of 'blocks' 
        blocks=[]
        block=None
        for line in f:
            line = line.strip()
            if re.match('^&', line): # Block starts with &
                if block:
                    blocks.append(block)
                block = line
            else: 
                block+=line
        blocks.append(block) # append final block
    return blocks

def parse_blocks(blocks):
    """
    Parse parameters from blocks and return Model oject
    """
    model = Model() # ASSUME one model per file

    vents = []
    surfs = []
    for block in blocks: # ASSUME one HEAD, REAC and SURF block per model
        if re.match('^&HEAD', block): 
            parse_HEAD(block, model)
        if re.match('^&REAC', block): 
            parse_REAC(block, model)
        if re.match('^&SURF', block):
            surfs.append(block)
        if re.match('^&VENT', block):
            vents.append(block)
            
    model_vents = [Vent() for i in range(len(vents))]
    for i in range(len(vents)):
        vent = model_vents[i]
        block = vents[i]
        parse_VENT(block, vent)
        model.add_VENT(vent)

    model_surfs = [Surf() for i in range(len(surfs))]
    for i in range(len(surfs)):
        surf = model_surfs[i]
        block = surfs[i]
        parse_SURF(block, surf)
        model.add_SURF(surf)
    return model

# ui
parser = argparse.ArgumentParser()
parser.add_argument('input', help='Pathway to input fds file')
parser.add_argument('-f', '--output', help='Pathway to output file, default: out.txt', default='out.txt')
args = parser.parse_args()
try:
    model = read_fds(args.input)
    print('Complete: ', args.output)
    s = model.print_summary()
    with open(args.output, 'w') as ff:
        ff.write(s)

except IOError as e:
    print(e.args)
    pass
except Exception as e:
    print("There was an error parsing file: ", e.args, e.__class__)
