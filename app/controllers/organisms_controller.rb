class OrganismsController < ApplicationController

  # GET /organisms
  # GET /organisms.json
  def index
    if params[:term]
      @organisms = Organism.where("code LIKE ? OR name LIKE ?","%#{params[:term]}%","%#{params[:term]}%")
    else
      @organisms = Organism.all
    end
    
    respond_to do |format|
      format.html
      format.json { render json: @organisms.map{|o| {value: o.code, label: "#{o.code} - #{o.name}"}}.to_json }
    end
  end

  # GET /organisms/1
  # GET /organisms/1.json
  def show
  end
end
