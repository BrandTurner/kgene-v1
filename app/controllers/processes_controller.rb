class ProcessesController < ApplicationController

  def index
    @processed_organisms = Organism.jobs
    
    if params[:org_code]
      organism = Organism.find_by(code: params[:org_code])
      organism.update_attributes(status: 'pending')
      ProcessJob.perform_async(organism.ids)
      # ProcessJob.new.async.perform(organism)
      # ActiveRecord::Base.connection_pool.with_connection do
      #   ::Gene.fetch_and_store_from_org(organism)
      #   ::Gene.fetch_and_store_orthologs_for_organism(organism)
      # end
      
      redirect_to processes_path
    end
  end
  
  def remove_results
    @organism = Organism.find(params[:organism_id])
    @organism.genes.destroy_all
    @organism.update_attributes(status: nil, job_error: nil)
    
    redirect_to processes_path
  end
  
  def explore_orthologs
    @organism = Organism.includes(:genes).where.not(genes: {ortholog_name: nil}).find(params[:organism_id])
  end
  
  def explore_no_orthologs
    @organism = Organism.includes(:genes).where(genes: {ortholog_name: nil}).find(params[:organism_id])
  end
  
  def download
    @organism = Organism.includes(:genes).find(params[:organism_id])
    
    f = CSV.open("tmp/#{@organism.id}.csv", "wb") do |csv|
      @organism.genes.order("ortholog_identity ASC NULLS LAST, genes.name ASC").each do |gene|
        csv << [gene.name, gene.description, gene.ortholog_description, gene.ortholog_species, gene.ortholog_length, gene.ortholog_sw_score, gene.ortholog_identity.nil? ? '' : sprintf('%.3f',gene.ortholog_identity)]
      end
    end
    
    send_file(
      "tmp/#{@organism.id}.csv",
      :filename    => "#{@organism.name.camelize}.csv",
      :type        => 'text/plain',
      :disposition => 'attachment',
      :streaming   => true,
      :buffer_size => 4096
    )
  end
end
