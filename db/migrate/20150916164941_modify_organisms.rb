class ModifyOrganisms < ActiveRecord::Migration
  def change
    add_column :organisms, :status, :string
    add_column :organisms, :job_error, :string, limit: 1000
  end
end
