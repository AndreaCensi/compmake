from load import list_categories, list_images, imread, rgb_from_string
 

def instance_category(context, category, path):
    images = list_images(path)
    for i, image_path in enumerate(images):
        with open(image_path, 'rb') as f:
            string = f.read()
        rgb = context.comp(rgb_from_string, string,
                           job_id='read-%s-%s' % (category, i))
        


if __name__ == '__main__':
    from compmake import Context
    c = Context()
    dataset = '101_ObjectCategories'

    categories = list_categories(dataset)
    
    for category, path in categories.items():
        c.comp_dynamic(instance_category, category, path,
                       job_id='instance-%s' % category)
            
    c.compmake_console()