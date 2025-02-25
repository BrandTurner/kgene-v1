require 'csv'
class GenesController < ApplicationController

  # GET /genes
  # GET /genes.json
  def index
    array = []
    @organism = Organism.find_by(code: params[:org_code])
    
    respond_to do |format|
      if @organism.nil?
        format.html { redirect_to root_path, notice: 'An organism must be selected' }
      else
        begin
          resource = RestClient::Resource.new "http://rest.kegg.jp/list/#{@organism.code}"
          resource.get.split("\n").each do |line|
            line.gsub!(/\"/,"\'")
            data = line.parse_csv({col_sep: "\t"})
            array.push data
          end
    
          @genes = array
        
          format.html
        rescue => e
          format.html { redirect_to root_path, notice: "There was an issue parsing the response from KEGG. Please contact the administrator. #{e}" }
        end
      end
    end
  end

  # GET /genes/1
  # GET /genes/1.json
  def show
  end
end