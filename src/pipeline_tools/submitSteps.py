#!/usr/bin/env python3 

import subprocess
import sys 
import glob
import os

pipeline_path = sys.path[0]
pipeline_tools_path = os.path.abspath(pipeline_path + "/pipeline_tools")
sys.path.append(pipeline_tools_path)
from slurmTools import *

def submitTrimming(configFileDict, FASTQ_PREFIX):
    """Function that submits slurm jobs for trimming reads.

    Args:
        configFileDict ([dict]): [configuration file dictionary]
        FASTQ_PREFIX ([lst]): [List containing the FASTQ sample IDs]

    Returns:
        [str]: comma separated string containing slurm job IDs for wait condition
    """    
    TRIM_JID_LIST = []
    for file in FASTQ_PREFIX:
        TRIM_CMD = "{bin} {parameters} -o {trimmed_dir}/{file}.trim_R1_001.fastq.gz -p {trimmed_dir}/{file}.trim_R2_001.fastq.gz {fastq_dir}/{file}_R1_001.fastq.gz {fastq_dir}/{file}_R2_001.fastq.gz".format(bin=configFileDict["cutadapt"], parameters=configFileDict["trim_reads"], file=file, trimmed_dir = configFileDict["trimmed_fastq_dir"], fastq_dir=configFileDict['fastq_dir'])
        
        
        SLURM_CMD = "{wsbatch} {slurm} -o {trimmed_log_dir}/{uid}_slurm-%j.out --wrap=\"{cmd}\"".format(wsbatch = configFileDict["wsbatch"], slurm = configFileDict["slurm_trim"], trimmed_log_dir = "{}/log".format(configFileDict["trimmed_fastq_dir"]), uid = configFileDict["uid"], cmd = TRIM_CMD)
        print(SLURM_CMD)
        
        out = subprocess.check_output(SLURM_CMD, shell=True, universal_newlines= True, stderr=subprocess.STDOUT)
        TRIM_JID_LIST.append(catchJID(out))
        
        configFileDict['trim_log_files'].append(getSlurmLog("{}/log".format(configFileDict["trimmed_fastq_dir"]),configFileDict['uid'],out))
        #TRIM_JID_LIST.append('0') #### FOR DEBUGGING PURPOSES
        
    TRIM_WAIT = ",".join(TRIM_JID_LIST)
    #del TRIM_JID_LIST
    return TRIM_WAIT


def submitMappingBowtie(configFileDict, FASTQ_PREFIX, FASTQ_PATH):
    """[Submits jobs for Mapping using Bowtie2]

    Args:
        configFileDict ([dict]): [configuration file dictionary]
        FASTQ_FILES ([lst]): [List containing the FASTQ sample IDs]
        FASTQ_PATH [str]: Absolute path of the FASTQ files
    Returns:
        [str]: [Returns the slurm Job IDs so that the jobs of the next step can wait until mapping has finished]
    """  
    MAP_JID_LIST = []
    configFileDict['mapping_log_files'] = []
    for file in FASTQ_PREFIX:                                                        

        MAP_CMD = "{mapper} {parameters} -x {REFSEQ} -1 {dir}/{file}*_R1_001.fastq.gz -2 {dir}/{file}*_R2_001.fastq.gz | {samtools} view -b -h -o {bam_dir}/{file}.raw.bam && {samtools} sort -O BAM -o {sorted_bam_dir}/{file}.sortedByCoord.bam {bam_dir}/{file}.raw.bam".format(mapper=configFileDict['bowtie2'], parameters=configFileDict['bowtie_parameters'],dir=FASTQ_PATH,file=file, samtools = configFileDict["samtools"], bam_dir=configFileDict['bam_dir'], REFSEQ=configFileDict['reference_genome'], sorted_bam_dir=configFileDict['sorted_bam_dir'])
        
        
        if '1' in configFileDict['task_list']: 
            SLURM_CMD = "{wsbatch} {slurm} -o {log_dir}/{uid}_slurm-%j.out --dependency=afterany:{JID} --wrap=\"{cmd}\"".format(wsbatch = configFileDict["wsbatch"], slurm = configFileDict["slurm_mapping"], log_dir = "{}/log".format(configFileDict['bam_dir']), uid = configFileDict["uid"], cmd = MAP_CMD, JID=configFileDict["TRIM_WAIT"])
            print(SLURM_CMD)
        else: 
            SLURM_CMD = "{wsbatch} {slurm} -o {log_dir}/{uid}_slurm-%j.out --wrap=\"{cmd}\"".format(wsbatch = configFileDict["wsbatch"], slurm = configFileDict["slurm_mapping"], log_dir = f"{configFileDict['bam_dir']}/log", uid = configFileDict["uid"], cmd = MAP_CMD)
            print(SLURM_CMD)
        out = subprocess.check_output(SLURM_CMD, shell=True, universal_newlines= True, stderr=subprocess.STDOUT)
        MAP_JID_LIST.append(catchJID(out))
        
        configFileDict['mapping_log_files'].append(getSlurmLog("{}/log".format(configFileDict["bam_dir"]),configFileDict['uid'],out))
    
    MAP_WAIT = ",".join(MAP_JID_LIST)
    #del MAP_JID_LIST
    return MAP_WAIT


def submitPCRduplication(configFileDict,BAM_FILES):
    """[Submits jobs for marking PCR duplicated reads using PICARD]

    Args:
        configFileDict ([dict]): [configuration file dictionary]
        BAM_PATH ([lst]): [List containing the BAM file absolute path]

    Returns:
        [str]: [Returns the slurm Job IDs so that the jobs of the next step can wait until mapping has finished]
    """
    PCR_DUP_JID_LIST = []
          
    OUTPUT_DIR = configFileDict['marked_bam_dir']    
    for bam in BAM_FILES: 
        input = os.path.basename(bam).split(".")[0]
        OUTPUT_FILE = "{}/{}.sortedByCoord.Picard.bam".format(OUTPUT_DIR,input)
        print(OUTPUT_FILE)
        METRIX_FILE = "{}/{}.metrix".format(OUTPUT_DIR,input)
        print(METRIX_FILE)
        PCR_CMD = "{PICARD} MarkDuplicates I={input} O={output} M={metrix}".format(PICARD=configFileDict['picard'], input=bam, output=OUTPUT_FILE, metrix=METRIX_FILE)
        print(PCR_CMD)
        if '2' in configFileDict['task_list']:
            SLURM_CMD = "{wsbatch} {slurm} -o {log_dir}/{uid}_slurm-%j.out --dependency=afterany:{JID} --wrap=\"{cmd}\"".format(wsbatch = configFileDict["wsbatch"], slurm = configFileDict["slurm_general"], log_dir = "{}/log".format(OUTPUT_DIR), uid = configFileDict["uid"], cmd = PCR_CMD, JID=configFileDict['MAP_WAIT'])
            print(SLURM_CMD)
        else: 
            SLURM_CMD = "{wsbatch} {slurm} -o {log_dir}/{uid}_slurm-%j.out --wrap=\"{cmd}\"".format(wsbatch = configFileDict["wsbatch"], slurm = configFileDict["slurm_general"], log_dir = "{}/log".format(OUTPUT_DIR), uid = configFileDict["uid"], cmd = PCR_CMD)
        
        out = subprocess.check_output(SLURM_CMD, shell=True, universal_newlines=True, stderr=subprocess.STDOUT)
        PCR_DUPLICATION_WAIT = PCR_DUP_JID_LIST.append(catchJID(out))
        
        configFileDict['pcr_log_files'].append(getSlurmLog("{}/log".format(configFileDict["marked_bam_dir"]),configFileDict['uid'],out))
    
    PCR_DUPLICATION_WAIT = ",".join(PCR_DUP_JID_LIST)
    del PCR_DUP_JID_LIST 
    return PCR_DUPLICATION_WAIT

def submitFilteringBAM(configFileDict, BAM_FILES):
    """[Submits jobs for filtering and sorting BAM files]

    Args:
        configFileDict ([dict]): [configuration file dictionary]
        BAM_FILES ([lst]): [List containing the BAM files]

    Returns:
        [str]: [Returns the slurm Job IDs so that the jobs of the next step can wait until mapping has finished]
    """
    BAM_FILTER_JID_LIST = []
    OUTPUT_DIR = configFileDict['filtered_bam_dir']
    for bam in BAM_FILES:
        input_file = os.path.basename(bam).split(".")[0]
        OUTPUT_FILE = "{}/{}.QualTrim_NoDup_NochrM_SortedByCoord.bam".format(OUTPUT_DIR, input_file)
        
        FILTER_CMD = "{samtools} view {arguments} -@ 4 {input} | awk '{{if(\$3!='chrM'){{print}}}}' | samtools view -b -o {output_file} -@ 4 && samtools index {output_file} -@ 4".format(samtools = configFileDict['samtools'], arguments=configFileDict['PCR_duplicates_removal'], input = bam, output_file = OUTPUT_FILE)
        
        
        if '3' in configFileDict['task_list']: 
            SLURM_CMD = "{wsbatch} {slurm} -o {log_dir}/{uid}_slurm-%j.out --dependency=afterany:{JID} --wrap=\"{cmd}\"".format(wsbatch = configFileDict["wsbatch"], slurm = configFileDict["slurm_filter_bam"], log_dir = "{}/log".format(OUTPUT_DIR), uid = configFileDict["uid"], cmd = FILTER_CMD, JID=configFileDict['PCR_DUPLICATION_WAIT'])
            print(SLURM_CMD)
        else: 
            SLURM_CMD = "{wsbatch} {slurm} -o {log_dir}/{uid}_slurm-%j.out --wrap=\"{cmd}\"".format(wsbatch = configFileDict["wsbatch"], slurm = configFileDict["slurm_filter_bam"], log_dir = "{}/log".format(OUTPUT_DIR), uid = configFileDict["uid"], cmd = FILTER_CMD)
            
        out = subprocess.check_output(SLURM_CMD, shell=True, universal_newlines= True, stderr=subprocess.STDOUT)
        BAM_FILTER_JID_LIST.append(catchJID(out))
        
        configFileDict['filtering_log_files'].append(getSlurmLog("{}/log".format(configFileDict["filtered_bam_dir"]),configFileDict['uid'],out))
    
    FILTER_BAM_WAIT = ",".join(BAM_FILTER_JID_LIST)
    del BAM_FILTER_JID_LIST
    return FILTER_BAM_WAIT
    


        
def submitBAM2BW(configFileDict, BAM_FILES):
    """[Submits jobs for removal of PCR duplicated reads]

    Args:
        configFileDict ([dict]): [configuration file dictionary]
        BAM_BW [str]: Absolute path where BAM FILES are and where to write them. 

    Returns:
        [str]: [Returns the slurm Job IDs so that the jobs of the next step can wait until mapping has finished]
    """
    BW_JID_LIST = []
    OUTPUT_DIR = configFileDict['bw_dir']
    for bam in BAM_FILES:
        input_file = os.path.basename(bam).split(".")[0]
        OUTPUT_FILE = "{}/{}.bw".format(OUTPUT_DIR, input_file)
        
        BAM2BW_CMD = "{bamcoverage} {arguments} --bam {input} -o {output}".format(bamcoverage=configFileDict['bamCoverage'], arguments=configFileDict['bam2bw'], input=bam, output=OUTPUT_FILE)
        
        if '4' in configFileDict['task_list']:
            SLURM_CMD = "{wsbatch} {slurm} -o {log_dir}/{uid}_slurm-%j.out --dependency=afterany:{JID} --wrap=\"{cmd}\"".format(wsbatch = configFileDict["wsbatch"], slurm = configFileDict["slurm_general"], log_dir = "{}/log".format(OUTPUT_DIR), uid = configFileDict["uid"], cmd = BAM2BW_CMD, JID=configFileDict['FILTER_BAM_WAIT'])
            print(SLURM_CMD)
        else:
            SLURM_CMD = "{wsbatch} {slurm} -o {log_dir}/{uid}_slurm-%j.out --wrap=\"{cmd}\"".format(wsbatch = configFileDict["wsbatch"], slurm = configFileDict["slurm_general"], log_dir = "{}/log".format(OUTPUT_DIR), uid = configFileDict["uid"], cmd = BAM2BW_CMD)
            print(SLURM_CMD)
        out = subprocess.check_output(SLURM_CMD, shell=True, universal_newlines= True, stderr=subprocess.STDOUT)
        BW_JID_LIST.append(catchJID(out))

        configFileDict['bw_log_files'].append(getSlurmLog("{}/log".format(configFileDict["bw_dir"]),configFileDict['uid'],out))
        
        
    BAM2BW_WAIT = ",".join(BW_JID_LIST)
    del BW_JID_LIST
    return BAM2BW_WAIT
            
        
def submitBAM2BED(configFileDict, BAM_FILES):
    """[Submits jobs for removal of PCR duplicated reads]

    Args:
        configFileDict ([dict]): [configuration file dictionary]
        BAM_BW [str]: Absolute path where BAM FILES are and where to write them. 

    Returns:
        [str]: [Returns the slurm Job IDs so that the jobs of the next step can wait until mapping has finished]
    """
    BAM2BED_JID_LIST = []
    OUTPUT_DIR = configFileDict['bed_dir']
    for bam in BAM_FILES:
        input_file = os.path.basename(bam).split(".")[0]
        OUTPUT_FILE = "{}/{}.bed".format(OUTPUT_DIR, input_file)
    
        BAM2BED_CMD = "source {bam2bed} {bedtools} {input} {output}".format(bedtools=configFileDict['bedtools'],bam2bed=configFileDict['bam2bed_script'],input=bam, output=OUTPUT_FILE)
        
        if '4' in configFileDict['task_list']: 
            SLURM_CMD = "{wsbatch} {slurm} -o {log_dir}/{uid}_slurm-%j.out --dependency=afterany:{JID} --wrap=\"{cmd}\"".format(wsbatch = configFileDict["wsbatch"], slurm = configFileDict["slurm_general"], log_dir = "{}/log".format(OUTPUT_DIR), uid = configFileDict["uid"], cmd = BAM2BED_CMD, JID=configFileDict['FILTER_BAM_WAIT'])
            print(SLURM_CMD)
        else: 
            SLURM_CMD = "{wsbatch} {slurm} -o {log_dir}/{uid}_slurm-%j.out --wrap=\"{cmd}\"".format(wsbatch = configFileDict["wsbatch"], slurm = configFileDict["slurm_general"], log_dir = "{}/log".format(OUTPUT_DIR), uid = configFileDict["uid"], cmd = BAM2BED_CMD)
            print(SLURM_CMD)
            
        out = subprocess.check_output(SLURM_CMD, shell=True, universal_newlines= True, stderr=subprocess.STDOUT)
        BAM2BED_JID_LIST.append(catchJID(out))
        
        configFileDict['bam2bed_log_files'].append(getSlurmLog("{}/log".format(configFileDict["bed_dir"]),configFileDict['uid'],out))
        
        
    BAM2BED_WAIT = ",".join(BAM2BED_JID_LIST)
    del BAM2BED_JID_LIST
    return BAM2BED_WAIT

def submitExtendReads(configFileDict,BED_FILES):
    """[Submits jobs for removal of PCR duplicated reads]

    Args:
        configFileDict ([dict]): [configuration file dictionary]
        BAM_BW [str]: Absolute path where BAM FILES are and where to write them. 

    Returns:
        [str]: [Returns the slurm Job IDs so that the jobs of the next step can wait until mapping has finished]
    """
    EXTENDBED_JID_LIST = []
    OUTPUT_DIR = configFileDict['extended_bed_dir']
    for bam in BED_FILES:
        input_file = os.path.basename(bam).split(".")[0]
        OUTPUT_FILE = "{}/{}.extendedReads.bed".format(OUTPUT_DIR, input_file)
        
        EXTENDBED_CMD = "source {BIN} {input} {extension} {genomeFileExtension} {output}".format(BIN=configFileDict['extendReadsScript'], extension=configFileDict['extend_reads'], input=bam, genomeFileExtension=configFileDict['genomeFileSize'], output=OUTPUT_FILE)
        
        if '4' in configFileDict['task_list']: 
            SLURM_CMD = "{wsbatch} {slurm} -o {log_dir}/{uid}_slurm-%j.out --dependency=afterany:{JID} --wrap=\"{cmd}\"".format(wsbatch = configFileDict["wsbatch"], slurm = configFileDict["slurm_general"], log_dir = "{}/log".format(OUTPUT_DIR), uid = configFileDict["uid"], cmd = EXTENDBED_CMD, JID=configFileDict['BAM2BED_WAIT'])
        else: 
            SLURM_CMD = "{wsbatch} {slurm} -o {log_dir}/{uid}_slurm-%j.out --wrap=\"{cmd}\"".format(wsbatch = configFileDict["wsbatch"], slurm = configFileDict["slurm_general"], log_dir = "{}/log".format(OUTPUT_DIR), uid = configFileDict["uid"], cmd = EXTENDBED_CMD)
        out = subprocess.check_output(SLURM_CMD, shell=True, universal_newlines= True, stderr=subprocess.STDOUT)
        EXTENDBED_JID_LIST.append(catchJID(out))
        
        configFileDict['extend_log_files'].append(getSlurmLog("{}/log".format(configFileDict["extended_bed_dir"]),configFileDict['uid'],out))
        
    EXT_BED_WAIT = ",".join(EXTENDBED_JID_LIST)
    del EXTENDBED_JID_LIST
    return EXT_BED_WAIT


def submitPeakCalling(configFileDict,BED_FILES):
    """[Submits jobs peak calling]

    Args:
        configFileDict ([dict]): [configuration file dictionary]
        BED_FILES [str]: Absolute path where BAM FILES are and where to write them. 

    Returns:
        [str]: [Returns the slurm Job IDs so that the jobs of the next step can wait until mapping has finished]
    """
    PEAK_CALLING_JID_LIST = []
    OUTPUT_DIR = configFileDict['peaks_dir']
    for bam in BED_FILES:
        input_file = os.path.basename(bam).split(".")[0]
        OUTPUT_FILE = "{}/{}.MACS".format(OUTPUT_DIR, input_file)
        
        PEAKCALL_CMD = "{macs2} callpeak {arguments} -t {input} -n {prefix} --outdir {output}".format(macs2=configFileDict['macs2'], arguments=configFileDict['peak_calling'], input=bam, output=OUTPUT_FILE, prefix=input_file)
        
        if '6' in configFileDict['task_list']: 
            SLURM_CMD = "{wsbatch} {slurm} -o {log_dir}/{uid}_slurm-%j.out --dependency=afterany:{JID} --wrap=\"{cmd}\"".format(wsbatch = configFileDict["wsbatch"], slurm = configFileDict["slurm_peakCalling"], log_dir = "{}/log".format(OUTPUT_DIR), uid = configFileDict["uid"], cmd = PEAKCALL_CMD, JID=configFileDict['EXT_BED_WAIT'])
        else: 
            SLURM_CMD = "{wsbatch} {slurm} -o {log_dir}/{uid}_slurm-%j.out --wrap=\"{cmd}\"".format(wsbatch = configFileDict["wsbatch"], slurm = configFileDict["slurm_general"], log_dir = "{}/log".format(OUTPUT_DIR), uid = configFileDict["uid"], cmd = PEAKCALL_CMD)
        out = subprocess.check_output(SLURM_CMD, shell=True, universal_newlines= True, stderr=subprocess.STDOUT)
        PEAK_CALLING_JID_LIST.append(catchJID(out))
        
        configFileDict['peak_log_files'].append(getSlurmLog("{}/log".format(configFileDict["peaks_dir"]),configFileDict['uid'],out))
        
    PEAK_CALLING_WAIT = ",".join(PEAK_CALLING_JID_LIST)
    del PEAK_CALLING_JID_LIST
    return PEAK_CALLING_WAIT




def submitJobCheck(configFileDict, log_key, wait_key):
    log_files = configFileDict[log_key]
    for file in log_files: 
        cmd = "python3 {jobCheck} -w -log {file}".format(jobCheck=configFileDict['jobCheck'], file=file)
        SLURM_CMD = "{wsbatch} --dependency=afterany:{JID} -o {raw_log}/slurm-%j.out --wrap=\"{cmd}\"".format(wsbatch=configFileDict['wsbatch'], cmd=cmd, JID=wait_key, raw_log = configFileDict['raw_log'])
        out = subprocess.check_output(SLURM_CMD, shell=True, universal_newlines=True, stderr=subprocess.STDOUT)


def submitATACseqQC(configFileDict, BAM_FILES):
    ATACQC_JID_LIST = []
    OUTPUT_DIR = configFileDict['atacQC_dir']
    for bam in BAM_FILES:
        input_file = os.path.basename(bam).split(".")[0]
        
        ATACQC_CMD = "Rscript {BIN} {input} {output_dir}".format(BIN=configFileDict['ATACseqQC'],input = bam,output_dir = OUTPUT_DIR) 
        
        if '4' in configFileDict['task_list']:
            SLURM_CMD = "{wsbatch} {slurm} -o {log_dir}/{uid}_slurm-%j.out --dependency=afterany:{JID} --wrap=\"{cmd}\"".format(wsbatch = configFileDict["wsbatch"], slurm = configFileDict["slurm_general"], log_dir = "{}/log".format(OUTPUT_DIR), uid = configFileDict["uid"], cmd = ATACQC_CMD, JID=configFileDict['FILTER_BAM_WAIT'])
            print(SLURM_CMD)
        else:
            SLURM_CMD = "{wsbatch} {slurm} -o {log_dir}/{uid}_slurm-%j.out --wrap=\"{cmd}\"".format(wsbatch = configFileDict["wsbatch"], slurm = configFileDict["slurm_general"], log_dir = "{}/log".format(OUTPUT_DIR), uid = configFileDict["uid"], cmd = ATACQC_CMD)
            print(SLURM_CMD)
        out = subprocess.check_output(SLURM_CMD, shell=True, universal_newlines= True, stderr=subprocess.STDOUT)
        ATACQC_JID_LIST.append(catchJID(out))

        configFileDict['atacQC_log_files'].append(getSlurmLog("{}/log".format(configFileDict["atacQC_dir"]),configFileDict['uid'],out))
        
        
    ATACQC_WAIT = ",".join(ATACQC_JID_LIST)
    del ATACQC_JID_LIST
    return ATACQC_WAIT




def submitBamQC(configFileDict, BAM_FILES):
    BAMQC_JID_LIST = []
    OUTPUT_DIR = configFileDict['atacQC_dir']
    for bam in BAM_FILES:
        input_file = os.path.basename(bam).split(".")[0]
        output_file = f"{OUTPUT_DIR}/{input_file}_bamQC_stats.csv"
        
        BAMQC_CMD = "Rscript {BIN} {input} {output_dir}".format(BIN=configFileDict['bamQC'],input = bam,output_dir = output_file) 
        
        if '4' in configFileDict['task_list']:
            SLURM_CMD = "{wsbatch} {slurm} -o {log_dir}/{uid}_slurm-%j.out --dependency=afterany:{JID} --wrap=\"{cmd}\"".format(wsbatch = configFileDict["wsbatch"], slurm = configFileDict["slurm_general"], log_dir = "{}/log".format(OUTPUT_DIR), uid = configFileDict["uid"], cmd = BAMQC_CMD, JID=configFileDict['FILTER_BAM_WAIT'])
            print(SLURM_CMD)
        else:
            SLURM_CMD = "{wsbatch} {slurm} -o {log_dir}/{uid}_slurm-%j.out --wrap=\"{cmd}\"".format(wsbatch = configFileDict["wsbatch"], slurm = configFileDict["slurm_general"], log_dir = "{}/log".format(OUTPUT_DIR), uid = configFileDict["uid"], cmd = BAMQC_CMD)
            print(SLURM_CMD)
        out = subprocess.check_output(SLURM_CMD, shell=True, universal_newlines= True, stderr=subprocess.STDOUT)
        BAMQC_JID_LIST.append(catchJID(out))

        configFileDict['bamQC_log_files'].append(getSlurmLog("{}/log".format(configFileDict["atacQC_dir"]),configFileDict['uid'],out))
        
        
    BAMQC_WAIT = ",".join(BAMQC_JID_LIST)
    del BAMQC_JID_LIST
    return BAMQC_WAIT


def submitFastQC(configFileDict):
    FASTQC_JID_LIST = []
    OUTPUT_DIR = configFileDict['fastQC_dir']
    if '1' in configFileDict['task_list']: 
        DIRECTORIES = [configFileDict['fastq_dir'], configFileDict['trimmed_fastq_dir']]
    else:
        DIRECTORIES = [configFileDict['fastq_dir']]
    
    for DIR in DIRECTORIES:
        fastq_files = glob.glob(f"{DIR}/*fastq.gz")
        for fastq in fastq_files:
        
            FASTQC_CMD = "{fastqc} -o {output_dir} {fastq}".format(fastqc = configFileDict['FastQC'], output_dir = OUTPUT_DIR, fastq = fastq)
            if '1' in configFileDict['task_list']:
                SLURM_CMD = "{wsbatch} {slurm} -o {log_dir}/{uid}_slurm-%j.out --dependency=afterany:{JID} --wrap=\"{cmd}\"".format(wsbatch = configFileDict['wsbatch'], slurm = configFileDict['slurm_general'], log_dir = "{}/log".format(OUTPUT_DIR), uid = configFileDict['uid'],JID = configFileDict['TRIM_WAIT'], cmd = FASTQC_CMD)
                print(SLURM_CMD)
            else: 
                SLURM_CMD = "{wsbatch} {slurm} -o {log_dir}/{uid}_slurm-%j.out --wrap=\"{cmd}\"".format(wsbatch = configFileDict['wsbatch'], slurm = configFileDict['slurm_general'], log_dir = "{}/log".format(OUTPUT_DIR), uid = configFileDict['uid'], cmd = FASTQC_CMD)
                print(SLURM_CMD)
            out = subprocess.check_output(SLURM_CMD, shell=True, universal_newlines= True, stderr=subprocess.STDOUT)
            FASTQC_JID_LIST.append(catchJID(out))
            
            configFileDict['fastqQC_log_files'].append(getSlurmLog("{}/log".format(configFileDict["fastQC_dir"]),configFileDict['uid'],out))
        
    FASTQC_WAIT = ",".join(FASTQC_JID_LIST)
    del FASTQC_JID_LIST
    return FASTQC_WAIT

def submitMultiQC(configFileDict):
    MFASTQC_JID_LIST = []
    INPUT_DIR = configFileDict['fastQC_dir']
    OUTPUT_DIR = INPUT_DIR
    cmd = "{multiqc} -s -o {output_dir} {input_dir}".format(multiqc = configFileDict['multiQC'],output_dir = OUTPUT_DIR, input_dir = INPUT_DIR)
    SLURM_CMD = SLURM_CMD = "{wsbatch} {slurm} -o {log_dir}/{uid}_slurm-%j.out --dependency=afterany:{JID} --wrap=\"{cmd}\"".format(wsbatch = configFileDict['wsbatch'], slurm = configFileDict['slurm_general'], log_dir = "{}/log".format(OUTPUT_DIR), uid = configFileDict['uid'],JID = configFileDict['FASTQC_WAIT'], cmd = cmd)
    print(SLURM_CMD)
    
    out = subprocess.check_output(SLURM_CMD, shell=True, universal_newlines= True, stderr=subprocess.STDOUT)
    MFASTQC_JID_LIST.append(catchJID(out))
            
    configFileDict['multiqc_log_files'].append(getSlurmLog("{}/log".format(configFileDict["fastQC_dir"]),configFileDict['uid'],out))
    
    MFASTQC_WAIT = ",".join(MFASTQC_JID_LIST)
    del MFASTQC_JID_LIST
    return MFASTQC_WAIT

