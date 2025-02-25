require 'nokogiri'
require 'open-uri'
class OrthologsController < ApplicationController

  # GET /genes
  # GET /genes.json
  def index
    
    respond_to do |format|
      begin
        array = []
    
        doc = Nokogiri::HTML(open("https://www.kegg.jp/ssdb-bin/ssdb_best_best?org_gene=#{params[:org_gene]}&sort_by=sw_sp"))
        table = doc.at('pre').text.to_s
    
        table.split("\n").each_with_index do |line,i|
          next if i < 2
          (entry,definition) = line[0..54].split("\s")
          org_code = entry.split(':').first
          species = Organism.find_by(code: org_code)
          ko = line[55..62].strip
          len = line[63..69].strip
          sw_score = line[70..79].strip
          margin = line[81..85].strip
          bits = line[91..97].strip
          identity = line[98..107].strip
          overlap = line[108..115].strip
          best = line[116..121].strip
          hash = {entry: entry, definition: definition, species: species, ko: ko, len: len,
            sw_score: sw_score, margin: margin, bits: bits, identity: identity, overlap: overlap, best: best
          }
          array.push hash
        end
    
        @org_gene = params[:org_gene]
        @orthologs = array
        
        format.html
      rescue => e
        org_code = params[:org_gene].split(":").first
        format.html { redirect_to genes_path(org_code: org_code), notice: "There was an issue parsing the response from KEGG. Please contact the administrator. #{e}" }
      end
    end
  end

  # GET /genes/1
  # GET /genes/1.json
  def show
  end
end