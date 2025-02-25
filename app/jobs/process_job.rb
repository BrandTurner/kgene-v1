class ProcessJob 
  # include SuckerPunch::Job
  # SuckerPunch.logger = ::Logger.new('log/sucker_punch.log')
  # workers 4
  include Sidekiq::Worker
  
  def perform(organism_id)
    organism = Organism.find(organism_id)
    ActiveRecord::Base.connection_pool.with_connection do
      ::Gene.fetch_and_store_from_org(organism)
      ::Gene.fetch_and_store_orthologs_for_organism(organism)
    end
  end
end
